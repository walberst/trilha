import pytest

from app.services.risco import (
    calcular_score_risco,
    faixa_de_score,
    pontuacao_frequencia,
    pontuacao_recencia,
)


class TestPontuacaoRecencia:
    def test_sem_nenhum_evento_e_o_pior_caso(self):
        assert pontuacao_recencia(None) == 100.0

    @pytest.mark.parametrize(
        "dias,pontuacao_esperada",
        [
            (0, 0.0),
            (2, 0.0),
            (3, 25.0),
            (6, 25.0),
            (7, 55.0),
            (13, 55.0),
            (14, 80.0),
            (20, 80.0),
            (21, 100.0),
            (100, 100.0),
        ],
    )
    def test_degraus_de_recencia(self, dias, pontuacao_esperada):
        assert pontuacao_recencia(dias) == pontuacao_esperada


class TestPontuacaoFrequencia:
    def test_engajamento_igual_ao_esperado_e_risco_zero(self):
        assert pontuacao_frequencia(40.0, 40.0) == 0.0

    def test_engajamento_acima_do_esperado_nao_fica_negativo(self):
        assert pontuacao_frequencia(80.0, 40.0) == 0.0

    def test_nenhum_engajamento_e_risco_maximo(self):
        assert pontuacao_frequencia(0.0, 40.0) == 100.0

    def test_metade_do_esperado_e_metade_do_risco(self):
        assert pontuacao_frequencia(20.0, 40.0) == 50.0

    def test_esperado_zero_ou_negativo_nao_gera_divisao_por_zero(self):
        assert pontuacao_frequencia(10.0, 0.0) == 0.0


class TestCalcularScoreRisco:
    def test_pesos_iguais_e_media_simples(self):
        # recencia 0 (dias<=2), frequencia 100 (sem engajamento) -> media = 50
        score = calcular_score_risco(
            dias_sem_atividade=1, soma_pesos_janela=0.0, engajamento_esperado=40.0
        )
        assert score == 50.0

    def test_aluno_saudavel_fica_com_score_baixo(self):
        score = calcular_score_risco(
            dias_sem_atividade=0, soma_pesos_janela=40.0, engajamento_esperado=40.0
        )
        assert score == 0.0
        assert faixa_de_score(score) == "baixo"

    def test_aluno_sumido_fica_com_score_alto(self):
        score = calcular_score_risco(
            dias_sem_atividade=30, soma_pesos_janela=0.0, engajamento_esperado=40.0
        )
        assert score == 100.0
        assert faixa_de_score(score) == "alto"

    def test_pesos_customizados_dao_mais_importancia_a_recencia(self):
        score = calcular_score_risco(
            dias_sem_atividade=30,  # pontuacao 100
            soma_pesos_janela=40.0,  # pontuacao 0 (engajamento em dia)
            engajamento_esperado=40.0,
            peso_recencia=0.8,
            peso_frequencia=0.2,
        )
        assert score == 80.0

    def test_soma_dos_pesos_zero_e_invalida(self):
        with pytest.raises(ValueError):
            calcular_score_risco(1, 10.0, 40.0, peso_recencia=0.0, peso_frequencia=0.0)


class TestFaixaDeScore:
    @pytest.mark.parametrize(
        "score,faixa_esperada",
        [(0.0, "baixo"), (39.9, "baixo"), (40.0, "medio"), (69.9, "medio"), (70.0, "alto"), (100.0, "alto")],
    )
    def test_limites_das_faixas(self, score, faixa_esperada):
        assert faixa_de_score(score) == faixa_esperada
