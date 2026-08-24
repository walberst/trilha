import datetime as dt

from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base

FAIXAS_RISCO = ("baixo", "medio", "alto")
STATUS_MATRICULA = ("ativa", "trancada", "concluida", "cancelada")


def agora_utc() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Curso(Base):
    __tablename__ = "cursos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(1000))
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)

    turmas: Mapped[list["Turma"]] = relationship(
        back_populates="curso", cascade="all, delete-orphan"
    )


class Turma(Base):
    __tablename__ = "turmas"

    id: Mapped[int] = mapped_column(primary_key=True)
    curso_id: Mapped[int] = mapped_column(
        ForeignKey("cursos.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    data_inicio: Mapped[dt.date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[dt.date | None] = mapped_column(Date)
    # Quantidade de pontos de engajamento (soma de pesos de eventos) esperada
    # em uma janela de 14 dias para um aluno saudavel nesta turma. Usado como
    # referencia na componente de frequencia do score de risco.
    engajamento_esperado_14d: Mapped[float] = mapped_column(Float, default=40.0, nullable=False)
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)

    curso: Mapped[Curso] = relationship(back_populates="turmas")
    matriculas: Mapped[list["Matricula"]] = relationship(
        back_populates="turma", cascade="all, delete-orphan"
    )


class Aluno(Base):
    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)

    matriculas: Mapped[list["Matricula"]] = relationship(
        back_populates="aluno", cascade="all, delete-orphan"
    )


class Matricula(Base):
    __tablename__ = "matriculas"
    __table_args__ = (
        UniqueConstraint("aluno_id", "turma_id", name="uq_matricula_aluno_turma"),
        CheckConstraint(f"status IN {STATUS_MATRICULA}", name="ck_matricula_status"),
        CheckConstraint(f"faixa_risco IN {FAIXAS_RISCO}", name="ck_matricula_faixa_risco"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(
        ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False
    )
    turma_id: Mapped[int] = mapped_column(
        ForeignKey("turmas.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="ativa", nullable=False)
    data_matricula: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)

    # Estado incremental usado pelo calculo de risco, atualizado a cada evento
    # novo sem precisar reprocessar o historico bruto guardado no MongoDB.
    ultimo_evento_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_evento_tipo: Mapped[str | None] = mapped_column(String(50))
    soma_pesos_14d: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Defaults refletem o pior caso (nenhum evento ainda), mesmo valor que
    # calcular_score_risco(None, 0.0, ...) produziria; ficam consistentes ate
    # o primeiro evento real recalcular os dois campos juntos.
    score_risco: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    faixa_risco: Mapped[str] = mapped_column(String(10), default="alto", nullable=False)
    atualizado_em: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=agora_utc, onupdate=agora_utc
    )

    aluno: Mapped[Aluno] = relationship(back_populates="matriculas")
    turma: Mapped[Turma] = relationship(back_populates="matriculas")
    engajamentos_diarios: Mapped[list["EngajamentoDiario"]] = relationship(
        back_populates="matricula", cascade="all, delete-orphan"
    )


class EngajamentoDiario(Base):
    """Bucket diario de pontos de engajamento por matricula.

    Em vez de somar o historico completo de eventos do MongoDB a cada
    recalculo de score, mantemos so os buckets dos ultimos dias relevantes
    aqui no Postgres. Um novo evento incrementa (ou cria) o bucket do dia e
    buckets fora da janela de frequencia sao descartados, entao a soma usada
    no score sempre olha para poucas linhas indexadas, nunca para o log bruto.
    """

    __tablename__ = "engajamentos_diarios"
    __table_args__ = (
        UniqueConstraint("matricula_id", "data", name="uq_engajamento_matricula_dia"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    matricula_id: Mapped[int] = mapped_column(
        ForeignKey("matriculas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    data: Mapped[dt.date] = mapped_column(Date, nullable=False)
    soma_pesos: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    matricula: Mapped[Matricula] = relationship(back_populates="engajamentos_diarios")
