def test_health_responde_ok(cliente_api):
    resposta = cliente_api.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_health_ready_confere_postgres_e_mongo(cliente_api):
    resposta = cliente_api.get("/health/ready")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "pronto"}


def test_metricas_prometheus_expostas(cliente_api):
    resposta = cliente_api.get("/metrics")
    assert resposta.status_code == 200
    assert b"trilha_http_requisicoes_total" in resposta.content


def test_websocket_conecta_e_desconecta_sem_erro(cliente_api):
    with cliente_api.websocket_connect("/ws/turmas/1"):
        pass
