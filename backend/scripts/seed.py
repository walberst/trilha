"""Popula o banco com cursos, turmas, alunos, matriculas e um historico de
eventos de exemplo (com perfis de engajamento variados, para o painel do
professor nascer com alunos em baixo, medio e alto risco de verdade).

Nunca roda sozinho: e um passo manual e explicito, chamado com
`python -m scripts.seed` (ou `make seed`), justamente para quem for usar o
projeto para valer nao herdar dados fake sem pedir.
"""

import datetime as dt
import random

import structlog

from app.db.mongo import NOME_COLECAO_EVENTOS, garantir_indices, obter_banco_mongo
from app.db.postgres import SessionLocal, criar_schema
from app.logging_config import configurar_logging
from app.models.orm import Aluno, Curso, Matricula, Turma
from app.models.schemas import EventoComportamentoCriar
from app.services.eventos import processar_evento

logger = structlog.get_logger(__name__)

NOMES_ALUNOS = [
    "Ana Beatriz Souza",
    "Bruno Carvalho Lima",
    "Camila Ferreira Dias",
    "Daniel Alves Pereira",
    "Eduarda Martins Rocha",
    "Felipe Gomes Barbosa",
    "Gabriela Ribeiro Costa",
    "Henrique Nunes Cardoso",
    "Isabela Teixeira Moura",
    "Joao Vitor Correia",
    "Karina Duarte Pinto",
    "Lucas Mendes Azevedo",
    "Mariana Castro Freitas",
    "Nicolas Araujo Batista",
    "Olivia Ramos Siqueira",
    "Pedro Henrique Torres",
    "Quenia Farias Monteiro",
    "Rafael Cunha Xavier",
    "Sofia Vieira Andrade",
    "Thiago Peixoto Lopes",
    "Valentina Brito Cavalcante",
    "William Rezende Guimaraes",
    "Yasmin Tavares Nogueira",
    "Arthur Sales Cordeiro",
    "Beatriz Coelho Lacerda",
    "Caio Bezerra Marinho",
    "Debora Franco Salgado",
    "Enzo Pacheco Furtado",
    "Fernanda Melo Cavalcanti",
    "Gustavo Rocha Sampaio",
    "Helena Prado Barros",
    "Igor Cavalcanti Neves",
    "Julia Amaral Pimenta",
    "Kevin Moreira Sant'Anna",
    "Larissa Dantas Figueiredo",
    "Matheus Borges Vasconcelos",
]

CURSOS_SEED = [
    {
        "nome": "Python para Analise de Dados",
        "descricao": "Fundamentos de Python, pandas e visualizacao de dados para negocios",
        "turmas": [
            {"nome": "Turma 2026.1 - Noite", "engajamento_esperado_14d": 40.0},
        ],
    },
    {
        "nome": "Fundamentos de Desenvolvimento Web",
        "descricao": "HTML, CSS, JavaScript e uma introducao a APIs REST",
        "turmas": [
            {"nome": "Turma 2026.1 - Manha", "engajamento_esperado_14d": 45.0},
        ],
    },
]

# Cada perfil descreve um padrao de engajamento diferente ao longo dos
# ultimos 30 dias, para o conjunto de alunos gerado cobrir as tres faixas
# de risco de forma realista em vez de tudo cair na mesma faixa.
PERFIS_ENGAJAMENTO = ("engajado", "morno", "sumido", "novo_ativo")


def _gerar_eventos_perfil(perfil: str) -> list[tuple[int, str]]:
    eventos: list[tuple[int, str]] = []
    if perfil == "engajado":
        for dias_atras in range(29, -1, -2):
            eventos.append((dias_atras, random.choice(["login", "login", "video_assistido"])))
            if dias_atras % 6 == 0:
                eventos.append((dias_atras, "post_forum"))
            if dias_atras % 10 == 0:
                eventos.append((dias_atras, "prova_concluida"))
    elif perfil == "morno":
        for dias_atras in range(28, -1, -5):
            eventos.append((dias_atras, random.choice(["login", "video_assistido"])))
    elif perfil == "sumido":
        for dias_atras in range(29, 17, -3):
            eventos.append((dias_atras, random.choice(["login", "video_assistido", "post_forum"])))
    elif perfil == "novo_ativo":
        for dias_atras in range(4, -1, -1):
            eventos.append((dias_atras, random.choice(["login", "video_assistido"])))
    return eventos


def _email_a_partir_do_nome(nome: str, indice: int) -> str:
    partes = nome.lower().replace("'", "").split()
    return f"{partes[0]}.{partes[-1]}{indice}@exemplo.com"


def executar() -> None:
    configurar_logging()
    criar_schema()

    banco_mongo = obter_banco_mongo()
    garantir_indices(banco_mongo)
    colecao_eventos = banco_mongo[NOME_COLECAO_EVENTOS]

    sessao = SessionLocal()
    try:
        if sessao.query(Curso).count() > 0:
            logger.warning("seed_abortado_banco_ja_populado")
            return

        alunos = []
        for indice, nome in enumerate(NOMES_ALUNOS):
            aluno = Aluno(nome=nome, email=_email_a_partir_do_nome(nome, indice))
            sessao.add(aluno)
            alunos.append(aluno)
        sessao.commit()

        matriculas_criadas: list[Matricula] = []
        for curso_dado in CURSOS_SEED:
            curso = Curso(nome=curso_dado["nome"], descricao=curso_dado["descricao"])
            sessao.add(curso)
            sessao.flush()

            for turma_dado in curso_dado["turmas"]:
                turma = Turma(
                    curso_id=curso.id,
                    nome=turma_dado["nome"],
                    data_inicio=dt.date.today() - dt.timedelta(days=45),
                    engajamento_esperado_14d=turma_dado["engajamento_esperado_14d"],
                )
                sessao.add(turma)
                sessao.flush()

                alunos_da_turma = random.sample(alunos, k=min(len(alunos), 17))
                for aluno in alunos_da_turma:
                    matricula = Matricula(aluno_id=aluno.id, turma_id=turma.id)
                    sessao.add(matricula)
                    sessao.flush()
                    matriculas_criadas.append(matricula)
        sessao.commit()

        agora = dt.datetime.now(dt.UTC)
        total_eventos = 0
        for indice, matricula in enumerate(matriculas_criadas):
            perfil = PERFIS_ENGAJAMENTO[indice % len(PERFIS_ENGAJAMENTO)]
            for dias_atras, tipo in _gerar_eventos_perfil(perfil):
                timestamp_evento = agora - dt.timedelta(
                    days=dias_atras, hours=random.randint(0, 20)
                )
                evento = EventoComportamentoCriar(
                    matricula_id=matricula.id, tipo=tipo, timestamp=timestamp_evento
                )
                processar_evento(sessao, colecao_eventos, evento, agora=agora)
                total_eventos += 1

        logger.info(
            "seed_concluido",
            alunos=len(alunos),
            matriculas=len(matriculas_criadas),
            eventos=total_eventos,
        )
    finally:
        sessao.close()


if __name__ == "__main__":
    executar()
