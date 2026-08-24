def _criar_curso_turma(cliente_api, engajamento_esperado_14d=30.0):
    curso = cliente_api.post("/cursos", json={"nome": "Curso Risco"}).json()
    turma = cliente_api.post(
        "/turmas",
        json={
            "curso_id": curso["id"],
            "nome": "Turma Risco",
            "data_inicio": "2026-01-10",
            "engajamento_esperado_14d": engajamento_esperado_14d,
        },
    ).json()
    return curso, turma


def _criar_aluno(cliente_api, nome, email):
    return cliente_api.post("/alunos", json={"nome": nome, "email": email}).json()


def test_criar_aluno_e_matricula(cliente_api):
    _, turma = _criar_curso_turma(cliente_api)
    aluno = _criar_aluno(cliente_api, "Aluno Um", "aluno.um@exemplo.com")

    resposta = cliente_api.post(
        "/matriculas", json={"aluno_id": aluno["id"], "turma_id": turma["id"]}
    )
    assert resposta.status_code == 201
    matricula = resposta.json()
    # sem nenhum evento ainda, matricula nasce no pior caso das duas componentes
    assert matricula["faixa_risco"] == "alto"
    assert matricula["score_risco"] == 100.0


def test_matricular_o_mesmo_aluno_duas_vezes_e_conflito(cliente_api):
    _, turma = _criar_curso_turma(cliente_api)
    aluno = _criar_aluno(cliente_api, "Aluno Dois", "aluno.dois@exemplo.com")

    primeira = cliente_api.post(
        "/matriculas", json={"aluno_id": aluno["id"], "turma_id": turma["id"]}
    )
    assert primeira.status_code == 201

    segunda = cliente_api.post(
        "/matriculas", json={"aluno_id": aluno["id"], "turma_id": turma["id"]}
    )
    assert segunda.status_code == 409
    assert segunda.json()["codigo"] == "aluno_ja_matriculado"


def test_matricular_aluno_inexistente_e_404(cliente_api):
    _, turma = _criar_curso_turma(cliente_api)
    resposta = cliente_api.post("/matriculas", json={"aluno_id": 999999, "turma_id": turma["id"]})
    assert resposta.status_code == 404


def test_detalhe_da_matricula_traz_pontuacoes_calculadas(cliente_api):
    _, turma = _criar_curso_turma(cliente_api)
    aluno = _criar_aluno(cliente_api, "Aluno Tres", "aluno.tres@exemplo.com")
    matricula = cliente_api.post(
        "/matriculas", json={"aluno_id": aluno["id"], "turma_id": turma["id"]}
    ).json()

    resposta = cliente_api.get(f"/matriculas/{matricula['id']}")
    assert resposta.status_code == 200
    detalhe = resposta.json()
    assert detalhe["aluno"]["id"] == aluno["id"]
    assert detalhe["dias_sem_atividade"] is None
    assert detalhe["pontuacao_recencia"] == 100.0


def test_matricula_inexistente_no_detalhe_e_404(cliente_api):
    resposta = cliente_api.get("/matriculas/999999")
    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "matricula_nao_encontrada"


def test_listagem_de_alunos_por_risco_e_paginada_e_ordenavel(cliente_api):
    _, turma = _criar_curso_turma(cliente_api)
    for i in range(3):
        aluno = _criar_aluno(cliente_api, f"Aluno Pag {i}", f"aluno.pag{i}@exemplo.com")
        cliente_api.post("/matriculas", json={"aluno_id": aluno["id"], "turma_id": turma["id"]})

    resposta = cliente_api.get(
        f"/turmas/{turma['id']}/alunos", params={"tamanho_pagina": 2, "pagina": 1}
    )
    assert resposta.status_code == 200
    pagina = resposta.json()
    assert pagina["total"] == 3
    assert pagina["tamanho_pagina"] == 2
    assert len(pagina["itens"]) == 2
    assert pagina["total_paginas"] == 2

    segunda_pagina = cliente_api.get(
        f"/turmas/{turma['id']}/alunos", params={"tamanho_pagina": 2, "pagina": 2}
    )
    assert len(segunda_pagina.json()["itens"]) == 1


def test_listagem_de_alunos_por_risco_em_turma_inexistente_e_404(cliente_api):
    resposta = cliente_api.get("/turmas/999999/alunos")
    assert resposta.status_code == 404
