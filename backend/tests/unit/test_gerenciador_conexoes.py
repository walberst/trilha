import asyncio

from app.realtime.manager import GerenciadorConexoes


class WebSocketFalso:
    def __init__(self, falha_ao_enviar: bool = False) -> None:
        self.falha_ao_enviar = falha_ao_enviar
        self.aceito = False
        self.mensagens_recebidas: list[dict] = []

    async def accept(self) -> None:
        self.aceito = True

    async def send_json(self, mensagem: dict) -> None:
        if self.falha_ao_enviar:
            raise ConnectionError("conexao fechada")
        self.mensagens_recebidas.append(mensagem)


def test_transmite_apenas_para_conexoes_da_turma_correta():
    async def cenario():
        gerenciador = GerenciadorConexoes()
        ws_turma_1 = WebSocketFalso()
        ws_turma_2 = WebSocketFalso()
        await gerenciador.conectar(1, ws_turma_1)
        await gerenciador.conectar(2, ws_turma_2)

        await gerenciador.transmitir_para_turma(1, {"faixa_nova": "alto"})

        assert ws_turma_1.mensagens_recebidas == [{"faixa_nova": "alto"}]
        assert ws_turma_2.mensagens_recebidas == []

    asyncio.run(cenario())


def test_conexao_que_falha_ao_enviar_e_removida():
    async def cenario():
        gerenciador = GerenciadorConexoes()
        ws_com_falha = WebSocketFalso(falha_ao_enviar=True)
        await gerenciador.conectar(1, ws_com_falha)

        await gerenciador.transmitir_para_turma(1, {"faixa_nova": "alto"})
        # uma segunda transmissao nao deve tentar de novo (a conexao ja foi removida)
        await gerenciador.transmitir_para_turma(1, {"faixa_nova": "medio"})

        assert 1 not in gerenciador._conexoes_por_turma

    asyncio.run(cenario())


def test_desconectar_remove_a_turma_quando_fica_vazia():
    async def cenario():
        gerenciador = GerenciadorConexoes()
        ws = WebSocketFalso()
        await gerenciador.conectar(5, ws)
        gerenciador.desconectar(5, ws)
        assert 5 not in gerenciador._conexoes_por_turma

    asyncio.run(cenario())
