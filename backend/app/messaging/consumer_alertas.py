"""Relay que roda dentro do processo da API: consome o topico de alertas de
risco publicado pelo worker de eventos e repassa cada alerta para o
GerenciadorConexoes, que empurra a atualizacao via WebSocket para o painel do
professor.

O cliente do confluent-kafka e sincrono e bloqueante, entao o consumo roda em
uma thread separada; a entrega ao WebSocket precisa acontecer no loop de
eventos asyncio principal, por isso o `asyncio.run_coroutine_threadsafe`.
"""

import asyncio
import json
import threading

import structlog

from app.config import obter_configuracao
from app.realtime.manager import gerenciador_conexoes

logger = structlog.get_logger(__name__)


def _loop_consumo(loop: asyncio.AbstractEventLoop, parar: threading.Event) -> None:
    try:
        from confluent_kafka import Consumer
    except ImportError:
        logger.warning("confluent_kafka_indisponivel_relay_desligado")
        return

    settings = obter_configuracao()
    try:
        consumidor = Consumer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "group.id": settings.kafka_group_id_alertas,
                "auto.offset.reset": "latest",
            }
        )
        consumidor.subscribe([settings.kafka_topico_alertas])
    except Exception:
        logger.exception("falha_ao_iniciar_consumidor_alertas")
        return

    try:
        while not parar.is_set():
            msg = consumidor.poll(1.0)
            if msg is None or msg.error():
                continue
            try:
                alerta = json.loads(msg.value())
            except ValueError:
                logger.warning("alerta_invalido_descartado")
                continue
            asyncio.run_coroutine_threadsafe(
                gerenciador_conexoes.transmitir_para_turma(alerta["turma_id"], alerta), loop
            )
    finally:
        consumidor.close()


class RelayAlertasRisco:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()

    def iniciar(self) -> None:
        settings = obter_configuracao()
        if not settings.kafka_habilitado:
            logger.info("relay_alertas_desabilitado")
            return
        loop = asyncio.get_event_loop()
        self._thread = threading.Thread(target=_loop_consumo, args=(loop, self._parar), daemon=True)
        self._thread.start()
        logger.info("relay_alertas_iniciado")

    def parar(self) -> None:
        self._parar.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("relay_alertas_finalizado")


relay_alertas = RelayAlertasRisco()
