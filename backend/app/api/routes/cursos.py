from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.postgres import obter_sessao
from app.models.orm import Curso
from app.models.schemas import CursoCriar, CursoSaida
from app.services.erros import RecursoNaoEncontrado

router = APIRouter(prefix="/cursos", tags=["cursos"])


@router.post("", response_model=CursoSaida, status_code=status.HTTP_201_CREATED)
def criar_curso(dados: CursoCriar, sessao: Session = Depends(obter_sessao)) -> Curso:
    curso = Curso(**dados.model_dump())
    sessao.add(curso)
    sessao.commit()
    sessao.refresh(curso)
    return curso


@router.get("", response_model=list[CursoSaida])
def listar_cursos(sessao: Session = Depends(obter_sessao)) -> list[Curso]:
    return list(sessao.execute(select(Curso).order_by(Curso.nome)).scalars())


@router.get("/{curso_id}", response_model=CursoSaida)
def obter_curso(curso_id: int, sessao: Session = Depends(obter_sessao)) -> Curso:
    curso = sessao.get(Curso, curso_id)
    if curso is None:
        raise RecursoNaoEncontrado(f"Curso {curso_id} nao encontrado")
    return curso
