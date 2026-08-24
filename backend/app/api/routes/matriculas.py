import datetime as dt

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, obter_configuracao
from app.db.postgres import obter_sessao
from app.models.orm import Aluno, Matricula, Turma
from app.models.schemas import (
    AlunoSaida,
    DetalheAluno,
    MatriculaCriar,
    MatriculaSaida,
    TurmaSaida,
)
from app.services.erros import AlunoJaMatriculado, MatriculaNaoEncontrada, RecursoNaoEncontrado
from app.services.risco import calcular_score_risco, faixa_de_score, pontuacao_frequencia, pontuacao_recencia

router = APIRouter(prefix="/matriculas", tags=["matriculas"])


@router.post("", response_model=MatriculaSaida, status_code=status.HTTP_201_CREATED)
def criar_matricula(
    dados: MatriculaCriar,
    sessao: Session = Depends(obter_sessao),
    settings: Settings = Depends(obter_configuracao),
) -> Matricula:
    aluno = sessao.get(Aluno, dados.aluno_id)
    if aluno is None:
        raise RecursoNaoEncontrado(f"Aluno {dados.aluno_id} nao encontrado")

    turma = sessao.get(Turma, dados.turma_id)
    if turma is None:
        raise RecursoNaoEncontrado(f"Turma {dados.turma_id} nao encontrada")

    existente = sessao.execute(
        select(Matricula).where(Matricula.aluno_id == dados.aluno_id, Matricula.turma_id == dados.turma_id)
    ).scalar_one_or_none()
    if existente is not None:
        raise AlunoJaMatriculado(f"Aluno {dados.aluno_id} ja matriculado na turma {dados.turma_id}")

    # Uma matricula nova nunca teve nenhum evento, entao comeca no pior caso
    # das duas componentes (sem atividade recente, sem engajamento na janela).
    score_inicial = calcular_score_risco(
        dias_sem_atividade=None,
        soma_pesos_janela=0.0,
        engajamento_esperado=turma.engajamento_esperado_14d,
        peso_recencia=settings.peso_recencia,
        peso_frequencia=settings.peso_frequencia,
    )
    matricula = Matricula(
        aluno_id=dados.aluno_id,
        turma_id=dados.turma_id,
        score_risco=score_inicial,
        faixa_risco=faixa_de_score(score_inicial),
    )
    sessao.add(matricula)
    sessao.commit()
    sessao.refresh(matricula)
    return matricula


@router.get("/{matricula_id}", response_model=DetalheAluno)
def obter_detalhe_aluno(matricula_id: int, sessao: Session = Depends(obter_sessao)) -> DetalheAluno:
    matricula = sessao.get(Matricula, matricula_id)
    if matricula is None:
        raise MatriculaNaoEncontrada(f"Matricula {matricula_id} nao encontrada")

    aluno = sessao.get(Aluno, matricula.aluno_id)
    turma = sessao.get(Turma, matricula.turma_id)

    dias_sem_atividade = None
    if matricula.ultimo_evento_em is not None:
        agora = dt.datetime.now(dt.UTC)
        dias_sem_atividade = max((agora.date() - matricula.ultimo_evento_em.date()).days, 0)

    return DetalheAluno(
        matricula=MatriculaSaida.model_validate(matricula),
        aluno=AlunoSaida.model_validate(aluno),
        turma=TurmaSaida.model_validate(turma),
        dias_sem_atividade=dias_sem_atividade,
        pontuacao_recencia=pontuacao_recencia(dias_sem_atividade),
        pontuacao_frequencia=pontuacao_frequencia(matricula.soma_pesos_14d, turma.engajamento_esperado_14d),
    )
