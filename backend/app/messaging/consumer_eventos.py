"""Worker que consome o topico de eventos de comportamento, processa cada
evento (grava bruto no MongoDB, recalcula o score incremental no Postgres) e,
quando a faixa de risco de uma matricula muda, publica um alerta no topico de
alertas para o processo da API repassar via WebSocket ao painel do professor.

Roda como um processo separado (`python -m app.messaging.consumer_eventos`),
desacoplado da API: assim a ingestao de eventos escala e falha
independentemente do processo que atende requisicoes HTTP/WebSocket.
"""

import json
import signal
import sys

import structlog

from app.config import obter_configuracao
from app.db.mongo import NOME_COLECAO_EVENTOS, garantir_indices, obter_banco_mongo
from app.db.postgres import SessionLocal, criar_schema
from app.logging_config import configurar_logging
from app.messaging.producer import ProdutorEventos
from app.metrics import alertas_risco_total, eventos_processados_total
from app.models.schemas import EventoComportamentoCriar
from app.services.erros import MatriculaNaoEncontrada
from app.services.eventos import processar_evento

logger = structlog.get_logger(__name__)


class _SinalizadorParada:
    def __init__(self) -> None:
        self.deve_parar = False

    def solicitar_parada(self, *_args) -> None:
        self.deve_parar = True


def executar() -> None:
    configurar_logging()
    settings = obter_configuracao()
    criar_schema()

    banco_mongo = obter_banco_mongo()
    garantir_indices(banco_mongo)
    colecao_eventos = banco_mongo[NOME_COLECAO_EVENTOS]

    produtor_alertas = ProdutorEventos(settings.kafka_bootstrap_servers)

    from confluent_kafka import Consumer

    consumidor = Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_group_id_consumidor,
            "auto.offset.reset": "earliest",
        }
    )
    consumidor.subscribe([settings.kafka_topico_eventos])

    sinalizador = _SinalizadorParada()
    signal.signal(signal.SIGTERM, sinalizador.solicitar_parada)
    signal.signal(signal.SIGINT, sinalizador.solicitar_parada)

    logger.info("consumidor_eventos_iniciado", topico=settings.kafka_topico_eventos)

    try:
        while not sinalizador.deve_parar:
            msg = consumidor.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.warning("erro_kafka", erro=str(msg.error()))
                continue

            try:
                payload = json.loads(msg.value())
                evento = EventoComportamentoCriar.model_validate(payload)
            except Exception:
                logger.exception("evento_invalido_descartado", payload=msg.value())
                continue

            sessao = SessionLocal()
            try:
                resultado = processar_evento(sessao, colecao_eventos, evento)
            except MatriculaNaoEncontrada:
                logger.warning(
                    "evento_para_matricula_inexistente", matricula_id=evento.matricula_id
                )
                continue
            finally:
                sessao.close()

            eventos_processados_total.labels(tipo=evento.tipo).inc()

            if resultado.mudou_de_faixa:
                alertas_risco_total.labels(
                    faixa_anterior=resultado.faixa_anterior, faixa_nova=resultado.faixa_nova
                ).inc()
                alerta = {
                    "matricula_id": resultado.matricula.id,
                    "aluno_id": resultado.matricula.aluno_id,
                    "turma_id": resultado.matricula.turma_id,
                    "faixa_anterior": resultado.faixa_anterior,
                    "faixa_nova": resultado.faixa_nova,
                    "score_risco": resultado.matricula.score_risco,
                }
                produtor_alertas.publicar(
                    settings.kafka_topico_alertas, chave=str(resultado.matricula.id), valor=alerta
                )
                logger.info("alerta_risco_publicado", **alerta)
    finally:
        consumidor.close()
        produtor_alertas.flush()
        logger.info("consumidor_eventos_parado")


if __name__ == "__main__":
    executar()
    sys.exit(0)
