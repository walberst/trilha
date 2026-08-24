from math import ceil
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.postgres import obter_sessao
from app.models.orm import Aluno, Curso, Matricula, Turma
from app.models.schemas import (
    AlunoComRisco,
    PaginaAlunosComRisco,
    TurmaCriar,
    TurmaSaida,
)
from app.services.erros import RecursoNaoEncontrado

router = APIRouter(prefix="/turmas", tags=["turmas"])


@router.post("", response_model=TurmaSaida, status_code=status.HTTP_201_CREATED)
def criar_turma(dados: TurmaCriar, sessao: Session = Depends(obter_sessao)) -> Turma:
    curso = sessao.get(Curso, dados.curso_id)
    if curso is None:
        raise RecursoNaoEncontrado(f"Curso {dados.curso_id} nao encontrado")

    turma = Turma(**dados.model_dump())
    sessao.add(turma)
    sessao.commit()
    sessao.refresh(turma)
    return turma


@router.get("", response_model=list[TurmaSaida])
def listar_turmas(curso_id: int | None = None, sessao: Session = Depends(obter_sessao)) -> list[Turma]:
    consulta = select(Turma).order_by(Turma.data_inicio.desc())
    if curso_id is not None:
        consulta = consulta.where(Turma.curso_id == curso_id)
    return list(sessao.execute(consulta).scalars())


@router.get("/{turma_id}", response_model=TurmaSaida)
def obter_turma(turma_id: int, sessao: Session = Depends(obter_sessao)) -> Turma:
    turma = sessao.get(Turma, turma_id)
    if turma is None:
        raise RecursoNaoEncontrado(f"Turma {turma_id} nao encontrada")
    return turma


@router.get("/{turma_id}/alunos", response_model=PaginaAlunosComRisco)
def listar_alunos_por_risco(
    turma_id: int,
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=20, ge=1, le=100),
    ordenar_por: Literal["risco", "nome", "ultimo_evento"] = Query(default="risco"),
    direcao: Literal["asc", "desc"] = Query(default="desc"),
    sessao: Session = Depends(obter_sessao),
) -> PaginaAlunosComRisco:
    """Lista paginada dos alunos de uma turma, ordenavel por risco.

    E o endpoint principal do painel do professor: por padrao ja vem
    ordenado do maior para o menor risco, para o professor bater o olho e
    ver quem precisa de atencao primeiro.
    """
    turma = sessao.get(Turma, turma_id)
    if turma is None:
        raise RecursoNaoEncontrado(f"Turma {turma_id} nao encontrada")

    colunas_ordenacao = {
        "risco": Matricula.score_risco,
        "nome": Aluno.nome,
        "ultimo_evento": Matricula.ultimo_evento_em,
    }
    coluna = colunas_ordenacao[ordenar_por]
    ordenacao = coluna.desc() if direcao == "desc" else coluna.asc()

    consulta_base = (
        select(Matricula, Aluno).join(Aluno, Aluno.id == Matricula.aluno_id).where(Matricula.turma_id == turma_id)
    )

    total = sessao.execute(select(func.count()).select_from(consulta_base.subquery())).scalar_one()

    linhas = sessao.execute(
        consulta_base.order_by(ordenacao, Matricula.id).offset((pagina - 1) * tamanho_pagina).limit(tamanho_pagina)
    ).all()

    itens = [
        AlunoComRisco(
            matricula_id=matricula.id,
            aluno_id=aluno.id,
            nome=aluno.nome,
            email=aluno.email,
            status=matricula.status,
            score_risco=matricula.score_risco,
            faixa_risco=matricula.faixa_risco,
            ultimo_evento_em=matricula.ultimo_evento_em,
            atualizado_em=matricula.atualizado_em,
        )
        for matricula, aluno in linhas
    ]

    return PaginaAlunosComRisco(
        itens=itens,
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
        total_paginas=ceil(total / tamanho_pagina) if total else 0,
    )
