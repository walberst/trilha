from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import obter_configuracao


class Base(DeclarativeBase):
    """Classe base declarativa compartilhada por todos os modelos ORM."""


def criar_engine_padrao():
    settings = obter_configuracao()
    if settings.database_url.startswith("sqlite"):
        # So usado em testes/dev sem Postgres real. SQLite exige uma conexao
        # unica compartilhada entre threads (StaticPool) porque o servidor
        # ASGI de teste roda a aplicacao numa thread separada da que abre a
        # conexao; sem isso o pool tenta fechar a conexao na thread errada.
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


engine = criar_engine_padrao()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def obter_sessao() -> Generator[Session, None, None]:
    """Dependencia do FastAPI: uma sessao por requisicao, fechada ao final."""
    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()


def criar_schema() -> None:
    """Cria as tabelas caso ainda nao existam. Nao apaga nem popula nada:
    o banco sobe limpo por padrao, o seed e um passo separado (scripts/seed.py).
    """
    Base.metadata.create_all(bind=engine)
