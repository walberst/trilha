import datetime as dt

import pytest

from app.models.orm import Aluno, Curso, Matricula, Turma
from app.models.schemas import EventoComportamentoCriar
from app.services.erros import MatriculaNaoEncontrada
from app.services.eventos import processar_evento


@pytest.fixture
def matricula_pronta(sessao_teste):
    curso = Curso(nome="Curso Teste")
    sessao_teste.add(curso)
    sessao_teste.flush()

    turma = Turma(
        curso_id=curso.id,
        nome="Turma Teste",
        data_inicio=dt.date.today() - dt.timedelta(days=60),
        engajamento_esperado_14d=20.0,
    )
    sessao_teste.add(turma)
    sessao_teste.flush()

    aluno = Aluno(nome="Aluno Teste", email="aluno.teste@exemplo.com")
    sessao_teste.add(aluno)
    sessao_teste.flush()

    matricula = Matricula(aluno_id=aluno.id, turma_id=turma.id)
    sessao_teste.add(matricula)
    sessao_teste.commit()
    sessao_teste.refresh(matricula)
    return matricula


def test_evento_para_matricula_inexistente_leva_erro(sessao_teste, colecao_eventos_teste):
    evento = EventoComportamentoCriar(matricula_id=999999, tipo="login")
    with pytest.raises(MatriculaNaoEncontrada):
        processar_evento(sessao_teste, colecao_eventos_teste, evento)


def test_evento_grava_documento_bruto_no_mongo(
    sessao_teste, colecao_eventos_teste, matricula_pronta
):
    evento = EventoComportamentoCriar(matricula_id=matricula_pronta.id, tipo="video_assistido")
    processar_evento(sessao_teste, colecao_eventos_teste, evento)

    documentos = list(colecao_eventos_teste.find({"matricula_id": matricula_pronta.id}))
    assert len(documentos) == 1
    assert documentos[0]["tipo"] == "video_assistido"
    assert documentos[0]["peso"] == 2.0


def test_evento_recente_e_frequente_deixa_matricula_em_baixo_risco(
    sessao_teste, colecao_eventos_teste, matricula_pronta
):
    agora = dt.datetime.now(dt.UTC)
    # engajamento_esperado_14d=20 na turma; 5 provas concluidas (peso 5) = 25, acima do esperado
    for _ in range(5):
        evento = EventoComportamentoCriar(
            matricula_id=matricula_pronta.id, tipo="prova_concluida", timestamp=agora
        )
        resultado = processar_evento(sessao_teste, colecao_eventos_teste, evento, agora=agora)

    assert resultado.matricula.faixa_risco == "baixo"
    assert resultado.matricula.soma_pesos_14d == 25.0


def test_matricula_sem_eventos_recentes_fica_em_alto_risco(
    sessao_teste, colecao_eventos_teste, matricula_pronta
):
    agora = dt.datetime.now(dt.UTC)
    evento_antigo = agora - dt.timedelta(days=25)
    evento = EventoComportamentoCriar(
        matricula_id=matricula_pronta.id, tipo="login", timestamp=evento_antigo
    )

    resultado = processar_evento(sessao_teste, colecao_eventos_teste, evento, agora=agora)

    assert resultado.dias_sem_atividade == 25
    assert resultado.matricula.soma_pesos_14d == 0.0
    assert resultado.matricula.faixa_risco == "alto"


def test_mudanca_de_faixa_e_sinalizada_corretamente(
    sessao_teste, colecao_eventos_teste, matricula_pronta
):
    agora = dt.datetime.now(dt.UTC)

    # matricula comeca em "alto" (default). Um evento forte de hoje deve derrubar para baixo.
    assert matricula_pronta.faixa_risco == "alto"

    evento = EventoComportamentoCriar(
        matricula_id=matricula_pronta.id, tipo="prova_concluida", timestamp=agora
    )
    resultado = processar_evento(sessao_teste, colecao_eventos_teste, evento, agora=agora)

    assert resultado.faixa_anterior == "alto"
    assert resultado.mudou_de_faixa is (resultado.faixa_nova != "alto")


def test_buckets_fora_da_janela_de_frequencia_sao_podados(
    sessao_teste, colecao_eventos_teste, matricula_pronta
):
    agora = dt.datetime.now(dt.UTC)
    evento_fora_da_janela = agora - dt.timedelta(days=20)
    evento = EventoComportamentoCriar(
        matricula_id=matricula_pronta.id, tipo="prova_concluida", timestamp=evento_fora_da_janela
    )
    resultado = processar_evento(sessao_teste, colecao_eventos_teste, evento, agora=agora)

    # o evento de 20 dias atras esta fora da janela de 14 dias: nao deve contar na soma
    assert resultado.matricula.soma_pesos_14d == 0.0
