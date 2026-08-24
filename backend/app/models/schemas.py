import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

TipoEvento = Literal["video_assistido", "prova_concluida", "login", "post_forum"]
FaixaRisco = Literal["baixo", "medio", "alto"]
StatusMatricula = Literal["ativa", "trancada", "concluida", "cancelada"]

# Peso de cada tipo de evento na formula de frequencia. Prova concluida e o
# sinal mais forte de engajamento real, login sozinho e o mais fraco.
PESOS_EVENTO: dict[str, float] = {
    "login": 1.0,
    "video_assistido": 2.0,
    "post_forum": 3.0,
    "prova_concluida": 5.0,
}


# --- Curso ---------------------------------------------------------------


class CursoCriar(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    descricao: str | None = Field(default=None, max_length=1000)


class CursoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    descricao: str | None
    criado_em: dt.datetime


# --- Turma -----------------------------------------------------------------


class TurmaCriar(BaseModel):
    curso_id: int
    nome: str = Field(min_length=2, max_length=200)
    data_inicio: dt.date
    data_fim: dt.date | None = None
    engajamento_esperado_14d: float = Field(default=40.0, gt=0)


class TurmaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    curso_id: int
    nome: str
    data_inicio: dt.date
    data_fim: dt.date | None
    engajamento_esperado_14d: float
    criado_em: dt.datetime


# --- Aluno -------------------------------------------------------------


class AlunoCriar(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    email: EmailStr


class AlunoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    criado_em: dt.datetime


# --- Matricula ---------------------------------------------------------


class MatriculaCriar(BaseModel):
    aluno_id: int
    turma_id: int


class MatriculaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    turma_id: int
    status: StatusMatricula
    data_matricula: dt.datetime
    ultimo_evento_em: dt.datetime | None
    ultimo_evento_tipo: str | None
    soma_pesos_14d: float
    score_risco: float
    faixa_risco: FaixaRisco
    atualizado_em: dt.datetime


class AlunoComRisco(BaseModel):
    """Linha usada na listagem paginada de alunos de uma turma por risco."""

    model_config = ConfigDict(from_attributes=True)

    matricula_id: int
    aluno_id: int
    nome: str
    email: str
    status: StatusMatricula
    score_risco: float
    faixa_risco: FaixaRisco
    ultimo_evento_em: dt.datetime | None
    atualizado_em: dt.datetime


class DetalheAluno(BaseModel):
    """Payload da tela de detalhe de um aluno numa turma."""

    matricula: MatriculaSaida
    aluno: AlunoSaida
    turma: TurmaSaida
    dias_sem_atividade: int | None
    pontuacao_recencia: float
    pontuacao_frequencia: float


# --- Evento de comportamento --------------------------------------------


class EventoComportamentoCriar(BaseModel):
    matricula_id: int
    tipo: TipoEvento
    timestamp: dt.datetime | None = None
    metadados: dict = Field(default_factory=dict)


class EventoComportamentoSaida(BaseModel):
    matricula_id: int
    aluno_id: int
    turma_id: int
    tipo: TipoEvento
    peso: float
    timestamp: dt.datetime
    metadados: dict


# --- Paginacao genérica --------------------------------------------------


class ParametrosPaginacao(BaseModel):
    pagina: int = Field(default=1, ge=1)
    tamanho_pagina: int = Field(default=20, ge=1, le=100)


class PaginaAlunosComRisco(BaseModel):
    itens: list[AlunoComRisco]
    total: int
    pagina: int
    tamanho_pagina: int
    total_paginas: int


# --- Erros -----------------------------------------------------------------


class ErroResposta(BaseModel):
    detalhe: str
    codigo: str
