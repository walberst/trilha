from app.api.routes.eventos import obter_produtor_eventos
from app.main import app
from tests.conftest import ProdutorFalso


def test_publicar_evento_usa_o_produtor_configurado(cliente_api):
    produtor_falso = ProdutorFalso()
    app.dependency_overrides[obter_produtor_eventos] = lambda: produtor_falso
    try:
        resposta = cliente_api.post("/eventos", json={"matricula_id": 1, "tipo": "login"})
        assert resposta.status_code == 202
        assert resposta.json() == {"status": "aceito"}
        assert len(produtor_falso.publicados) == 1
        topico, chave, valor = produtor_falso.publicados[0]
        assert chave == "1"
        assert valor["tipo"] == "login"
    finally:
        app.dependency_overrides.pop(obter_produtor_eventos, None)


def test_publicar_evento_com_tipo_invalido_e_422(cliente_api):
    # O FastAPI resolve as dependencias da rota (incluindo o produtor Kafka)
    # antes de decidir que o corpo e invalido, entao mesmo uma requisicao que
    # vai falhar validacao passa pelo Depends(obter_produtor_eventos). Sem
    # substituir por um produtor falso, o teste exigiria um broker Kafka de
    # verdade so para chegar no erro 422.
    app.dependency_overrides[obter_produtor_eventos] = lambda: ProdutorFalso()
    try:
        resposta = cliente_api.post(
            "/eventos", json={"matricula_id": 1, "tipo": "tipo_que_nao_existe"}
        )
        assert resposta.status_code == 422
    finally:
        app.dependency_overrides.pop(obter_produtor_eventos, None)
