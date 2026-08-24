def test_fluxo_completo_criar_curso_turma_e_listar(cliente_api):
    resposta_curso = cliente_api.post("/cursos", json={"nome": "Python Basico", "descricao": "Introdutorio"})
    assert resposta_curso.status_code == 201
    curso_id = resposta_curso.json()["id"]

    resposta_turma = cliente_api.post(
        "/turmas",
        json={
            "curso_id": curso_id,
            "nome": "Turma A",
            "data_inicio": "2026-01-10",
            "engajamento_esperado_14d": 30.0,
        },
    )
    assert resposta_turma.status_code == 201
    turma = resposta_turma.json()
    assert turma["curso_id"] == curso_id

    resposta_listagem = cliente_api.get("/turmas", params={"curso_id": curso_id})
    assert resposta_listagem.status_code == 200
    assert len(resposta_listagem.json()) == 1


def test_criar_turma_para_curso_inexistente_retorna_404(cliente_api):
    resposta = cliente_api.post(
        "/turmas", json={"curso_id": 999999, "nome": "Turma X", "data_inicio": "2026-01-10"}
    )
    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "recurso_nao_encontrado"


def test_obter_curso_inexistente_retorna_404(cliente_api):
    resposta = cliente_api.get("/cursos/999999")
    assert resposta.status_code == 404


def test_criar_curso_com_nome_curto_e_invalido(cliente_api):
    resposta = cliente_api.post("/cursos", json={"nome": "A"})
    assert resposta.status_code == 422
