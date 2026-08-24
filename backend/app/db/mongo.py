from functools import lru_cache

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database

from app.config import obter_configuracao

NOME_COLECAO_EVENTOS = "eventos_comportamento"


@lru_cache
def obter_cliente_mongo() -> MongoClient:
    settings = obter_configuracao()
    return MongoClient(settings.mongo_url)


def obter_banco_mongo() -> Database:
    """Dependencia do FastAPI para acesso ao banco de eventos brutos."""
    settings = obter_configuracao()
    cliente = obter_cliente_mongo()
    return cliente[settings.mongo_database]


def garantir_indices(banco: Database) -> None:
    colecao = banco[NOME_COLECAO_EVENTOS]
    colecao.create_index([("matricula_id", ASCENDING), ("timestamp", ASCENDING)])
    colecao.create_index([("aluno_id", ASCENDING)])
