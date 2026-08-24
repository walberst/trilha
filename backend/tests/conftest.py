"""Fixtures compartilhadas da suite.

Os testes de integracao rodam contra SQLite em memoria (no lugar do Postgres
real) e mongomock (no lugar do MongoDB real). Isso evita depender de
containers/testcontainers so para rodar `pytest`, mantendo a suite rapida e
sem infraestrutura externa; localmente ou no CI, a mesma logica de negocio
(services/eventos.py, services/risco.py) e exercitada de ponta a ponta, so a
camada de conexao com o banco e trocada.
"""

import os

# Precisa ser definido antes de qualquer import de app.config/app.db, para o
# engine padrao (usado no startup da aplicacao) nunca tentar abrir uma
# conexao de verdade com Postgres/Kafka durante a suite.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("OTEL_HABILITADO", "false")
os.environ.setdefault("KAFKA_HABILITADO", "false")

import mongomock  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import obter_configuracao  # noqa: E402

obter_configuracao.cache_clear()

import app.main as main_module  # noqa: E402
from app.db.mongo import obter_banco_mongo  # noqa: E402
from app.db.postgres import Base, obter_sessao  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def engine_teste():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def fabrica_sessao_teste(engine_teste):
    return sessionmaker(bind=engine_teste, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def sessao_teste(fabrica_sessao_teste):
    sessao = fabrica_sessao_teste()
    yield sessao
    sessao.close()


@pytest.fixture
def mongo_teste():
    cliente = mongomock.MongoClient()
    return cliente["trilha_eventos_teste"]


@pytest.fixture
def colecao_eventos_teste(mongo_teste):
    return mongo_teste["eventos_comportamento"]


@pytest.fixture
def cliente_api(monkeypatch, fabrica_sessao_teste, mongo_teste):
    """TestClient com Postgres trocado por SQLite em memoria e MongoDB
    trocado por mongomock, tanto nas dependencias das rotas quanto no
    lifespan (que faz `garantir_indices` direto, sem passar por Depends).
    """

    def _obter_sessao_teste():
        sessao = fabrica_sessao_teste()
        try:
            yield sessao
        finally:
            sessao.close()

    def _obter_mongo_teste():
        return mongo_teste

    monkeypatch.setattr(main_module, "obter_banco_mongo", _obter_mongo_teste)
    app.dependency_overrides[obter_sessao] = _obter_sessao_teste
    app.dependency_overrides[obter_banco_mongo] = _obter_mongo_teste

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class ProdutorFalso:
    """Substitui o ProdutorEventos nos testes de API: guarda em memoria o que
    seria publicado no Kafka em vez de exigir um broker de verdade.
    """

    def __init__(self) -> None:
        self.publicados: list[tuple[str, str, dict]] = []

    def publicar(self, topico: str, chave: str, valor: dict) -> None:
        self.publicados.append((topico, chave, valor))

    def flush(self, timeout: float = 5.0) -> None:
        return None
