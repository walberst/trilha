"""Gerenciador de conexoes WebSocket do painel do professor.

As conexoes sao agrupadas por turma porque o professor acompanha uma turma
por vez: so faz sentido empurrar a atualizacao de risco de um aluno para
quem esta olhando a turma dele.
"""

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class GerenciadorConexoes:
    def __init__(self) -> None:
        self._conexoes_por_turma: dict[int, set[WebSocket]] = {}

    async def conectar(self, turma_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._conexoes_por_turma.setdefault(turma_id, set()).add(websocket)
        logger.info("websocket_conectado", turma_id=turma_id)

    def desconectar(self, turma_id: int, websocket: WebSocket) -> None:
        conexoes = self._conexoes_por_turma.get(turma_id)
        if not conexoes:
            return
        conexoes.discard(websocket)
        if not conexoes:
            self._conexoes_por_turma.pop(turma_id, None)
        logger.info("websocket_desconectado", turma_id=turma_id)

    async def transmitir_para_turma(self, turma_id: int, mensagem: dict) -> None:
        conexoes = list(self._conexoes_por_turma.get(turma_id, ()))
        for websocket in conexoes:
            try:
                await websocket.send_json(mensagem)
            except Exception:
                logger.warning("falha_ao_enviar_websocket", turma_id=turma_id)
                self.desconectar(turma_id, websocket)


gerenciador_conexoes = GerenciadorConexoes()
