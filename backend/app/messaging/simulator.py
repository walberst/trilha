"""Simula a plataforma de curso publicando eventos de comportamento de alunos
matriculados no topico Kafka de ingestao. Serve para ter o pipeline inteiro
(produtor -> Kafka -> consumidor -> Postgres/MongoDB -> WebSocket) se
movendo em uma demonstracao local, sem depender de uma integracao real com
um LMS.

Roda como processo separado: `python -m app.messaging.simulator`.
"""

import random
import time

import structlog

from app.config import obter_configuracao
from app.db.postgres import SessionLocal
from app.logging_config import configurar_logging
from app.messaging.producer import ProdutorEventos
from app.models.orm import Matricula
from app.models.schemas import PESOS_EVENTO

logger = structlog.get_logger(__name__)

TIPOS_EVENTO = list(PESOS_EVENTO.keys())
# login e o evento mais comum e mais fraco, prova concluida e o mais raro e mais forte.
PESOS_SORTEIO = [4, 3, 2, 1]


def _matriculas_ativas() -> list[int]:
    sessao = SessionLocal()
    try:
        linhas = sessao.query(Matricula.id).filter(Matricula.status == "ativa").all()
        return [linha[0] for linha in linhas]
    finally:
        sessao.close()


def executar() -> None:
    configurar_logging()
    settings = obter_configuracao()
    produtor = ProdutorEventos(settings.kafka_bootstrap_servers)

    logger.info("simulador_iniciado", topico=settings.kafka_topico_eventos)
    while True:
        matriculas = _matriculas_ativas()
        if not matriculas:
            logger.warning("nenhuma_matricula_ativa_aguardando_seed")
            time.sleep(5)
            continue

        matricula_id = random.choice(matriculas)
        tipo = random.choices(TIPOS_EVENTO, weights=PESOS_SORTEIO)[0]
        evento = {"matricula_id": matricula_id, "tipo": tipo, "metadados": {}}
        produtor.publicar(settings.kafka_topico_eventos, chave=str(matricula_id), valor=evento)
        logger.info("evento_simulado_publicado", **evento)
        time.sleep(settings.simulador_intervalo_segundos)


if __name__ == "__main__":
    executar()
