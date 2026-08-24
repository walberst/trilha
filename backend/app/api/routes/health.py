from fastapi import APIRouter, Depends
from pymongo.database import Database
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.mongo import obter_banco_mongo
from app.db.postgres import obter_sessao

router = APIRouter(tags=["saude"])


@router.get("/health")
def saude() -> dict:
    """Liveness: o processo esta de pe. Nao depende de nenhuma infra externa."""
    return {"status": "ok"}


@router.get("/health/ready")
def prontidao(
    sessao: Session = Depends(obter_sessao),
    banco_mongo: Database = Depends(obter_banco_mongo),
) -> dict:
    """Readiness: as dependencias criticas (Postgres e MongoDB) respondem."""
    sessao.execute(text("SELECT 1"))
    banco_mongo.command("ping")
    return {"status": "pronto"}
