from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.manager import gerenciador_conexoes

router = APIRouter()


@router.websocket("/ws/turmas/{turma_id}")
async def canal_risco_turma(websocket: WebSocket, turma_id: int) -> None:
    """Canal do painel do professor: uma conexao por turma que recebe um
    evento a cada vez que a faixa de risco de um aluno daquela turma muda.

    O canal e so de saida (server -> cliente); qualquer mensagem recebida do
    cliente e descartada, ela so serve para manter a conexao viva.
    """
    await gerenciador_conexoes.conectar(turma_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        gerenciador_conexoes.desconectar(turma_id, websocket)
