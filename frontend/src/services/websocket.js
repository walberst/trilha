const WS_BASE_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

/**
 * Abre o canal de alertas de risco de uma turma. A reconexao e simples (com
 * backoff fixo) porque o canal so carrega notificacoes complementares: se
 * cair, a proxima chamada de listagem via REST ja traz o estado correto.
 */
export function conectarCanalRisco(turmaId, aoReceberAlerta) {
  let socket = null;
  let fechadoPeloConsumidor = false;

  function conectar() {
    socket = new WebSocket(`${WS_BASE_URL}/ws/turmas/${turmaId}`);

    socket.addEventListener("message", (evento) => {
      aoReceberAlerta(JSON.parse(evento.data));
    });

    socket.addEventListener("close", () => {
      if (!fechadoPeloConsumidor) {
        setTimeout(conectar, 3000);
      }
    });
  }

  conectar();

  return {
    fechar() {
      fechadoPeloConsumidor = true;
      socket?.close();
    },
  };
}
