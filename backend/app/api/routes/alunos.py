from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.postgres import obter_sessao
from app.models.orm import Aluno
from app.models.schemas import AlunoCriar, AlunoSaida
from app.services.erros import RecursoNaoEncontrado

router = APIRouter(prefix="/alunos", tags=["alunos"])


@router.post("", response_model=AlunoSaida, status_code=status.HTTP_201_CREATED)
def criar_aluno(dados: AlunoCriar, sessao: Session = Depends(obter_sessao)) -> Aluno:
    aluno = Aluno(**dados.model_dump())
    sessao.add(aluno)
    sessao.commit()
    sessao.refresh(aluno)
    return aluno


@router.get("", response_model=list[AlunoSaida])
def listar_alunos(sessao: Session = Depends(obter_sessao)) -> list[Aluno]:
    return list(sessao.execute(select(Aluno).order_by(Aluno.nome)).scalars())


@router.get("/{aluno_id}", response_model=AlunoSaida)
def obter_aluno(aluno_id: int, sessao: Session = Depends(obter_sessao)) -> Aluno:
    aluno = sessao.get(Aluno, aluno_id)
    if aluno is None:
        raise RecursoNaoEncontrado(f"Aluno {aluno_id} nao encontrado")
    return aluno
