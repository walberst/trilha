from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from sqlalchemy.exc import IntegrityError

from app.api.routes import alunos, cursos, eventos, health, matriculas, turmas, websocket
from app.config import obter_configuracao
from app.db.mongo import garantir_indices, obter_banco_mongo
from app.db.postgres import criar_schema, engine
from app.logging_config import configurar_logging
from app.messaging.consumer_alertas import relay_alertas
from app.metrics import MetricasMiddleware
from app.models.schemas import ErroResposta
from app.services.erros import ErroDominio
from app.telemetry import configurar_telemetria

configurar_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = obter_configuracao()
    criar_schema()
    garantir_indices(obter_banco_mongo())
    configurar_telemetria(app, engine)
    relay_alertas.iniciar()
    logger.info("aplicacao_iniciada", ambiente=settings.ambiente)
    yield
    relay_alertas.parar()
    logger.info("aplicacao_finalizada")


app = FastAPI(
    title="Trilha",
    description="Deteccao antecipada de risco de evasao em cursos online",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(MetricasMiddleware)
app.mount("/metrics", make_asgi_app())

app.include_router(health.router)
app.include_router(cursos.router)
app.include_router(turmas.router)
app.include_router(alunos.router)
app.include_router(matriculas.router)
app.include_router(eventos.router)
app.include_router(websocket.router)


@app.exception_handler(ErroDominio)
async def tratar_erro_dominio(_request: Request, erro: ErroDominio) -> JSONResponse:
    return JSONResponse(
        status_code=erro.status_http,
        content=ErroResposta(detalhe=str(erro), codigo=erro.codigo).model_dump(),
    )


@app.exception_handler(IntegrityError)
async def tratar_erro_integridade(_request: Request, _erro: IntegrityError) -> JSONResponse:
    # Rede de seguranca contra corrida entre a checagem de duplicidade feita
    # na rota e a constraint unica do banco: evita vazar um 500 por causa de
    # uma condicao de corrida em vez de um 409 de fato acionavel pelo cliente.
    return JSONResponse(
        status_code=409,
        content=ErroResposta(
            detalhe="Conflito de dados: recurso ja existe", codigo="conflito_dados"
        ).model_dump(),
    )
