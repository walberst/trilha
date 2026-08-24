"""Formula de score de risco de evasao.

O score combina duas componentes, cada uma em uma escala de 0 (sem risco) a
100 (risco maximo), e depois faz uma media ponderada das duas:

Recencia: ha quanto tempo o aluno nao gera nenhum evento de comportamento.
Um aluno sumido ha 3 semanas e um sinal de alerta mais forte do que um aluno
que fez login ontem mas engaja pouco. Usamos uma funcao em degraus (em vez de
uma reta continua) porque a diferenca entre "sumiu ha 2 dias" e "sumiu ha 6
dias" e pouco relevante na pratica, mas cruzar a marca de uma ou duas semanas
sem aparecer e o que realmente indica risco de abandono.

Frequencia: quanto o aluno gerou de engajamento (soma dos pesos dos eventos)
nos ultimos N dias (`janela_frequencia_dias`, 14 por padrao) comparado com o
que se espera de um aluno saudavel naquela turma. Um aluno pode ter feito
login ontem (recencia baixa) mas estar so logando sem assistir aula nem fazer
prova, o que a frequencia captura e a recencia sozinha nao pegaria.

O score final e round(media ponderada, 2), com faixas baixo/medio/alto risco.
Os pesos e faixas sao dados de configuracao (`app.config.Settings`), nao
constantes magicas espalhadas pelo codigo.
"""

DEGRAUS_RECENCIA: list[tuple[int, float]] = [
    (2, 0.0),
    (6, 25.0),
    (13, 55.0),
    (20, 80.0),
]
PONTUACAO_RECENCIA_MAXIMA = 100.0

LIMIAR_MEDIO = 40.0
LIMIAR_ALTO = 70.0


def pontuacao_recencia(dias_sem_atividade: int | None) -> float:
    """Quanto maior o numero de dias sem nenhum evento, maior a pontuacao.

    `None` significa que a matricula nunca teve nenhum evento registrado,
    o que e tratado como o pior caso (aluno matriculado mas nunca engajou).
    """
    if dias_sem_atividade is None:
        return PONTUACAO_RECENCIA_MAXIMA
    for limite_dias, pontuacao in DEGRAUS_RECENCIA:
        if dias_sem_atividade <= limite_dias:
            return pontuacao
    return PONTUACAO_RECENCIA_MAXIMA


def pontuacao_frequencia(soma_pesos_janela: float, engajamento_esperado: float) -> float:
    """Quanto mais abaixo do esperado para a turma, maior a pontuacao de risco.

    Um aluno que atinge ou supera o engajamento esperado tem pontuacao zero
    nesta componente, mesmo que ainda nao seja perfeito: o objetivo aqui e
    identificar deficit, nao premiar excesso.
    """
    if engajamento_esperado <= 0:
        return 0.0
    razao = soma_pesos_janela / engajamento_esperado
    if razao >= 1:
        return 0.0
    return round((1 - razao) * 100, 2)


def calcular_score_risco(
    dias_sem_atividade: int | None,
    soma_pesos_janela: float,
    engajamento_esperado: float,
    peso_recencia: float = 0.5,
    peso_frequencia: float = 0.5,
) -> float:
    pontuacao_r = pontuacao_recencia(dias_sem_atividade)
    pontuacao_f = pontuacao_frequencia(soma_pesos_janela, engajamento_esperado)
    total_pesos = peso_recencia + peso_frequencia
    if total_pesos <= 0:
        raise ValueError("A soma dos pesos de recencia e frequencia deve ser maior que zero")
    score = (pontuacao_r * peso_recencia + pontuacao_f * peso_frequencia) / total_pesos
    return round(score, 2)


def faixa_de_score(score: float) -> str:
    if score < LIMIAR_MEDIO:
        return "baixo"
    if score < LIMIAR_ALTO:
        return "medio"
    return "alto"
