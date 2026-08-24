"""Processamento de eventos de comportamento: grava o evento bruto no MongoDB
e atualiza o estado incremental usado no calculo de score de risco no Postgres.

Estrategia de recalculo incremental
------------------------------------
A ingestao de eventos e continua (via Kafka) e o volume bruto acumulado no
MongoDB cresce sem limite. Reprocessar todo o historico de um aluno a cada
evento novo para recalcular o score seria O(n) por evento, ficando cada vez
mais caro conforme o curso avanca.

Em vez disso, cada `Matricula` mantem um estado incremental no Postgres:
`ultimo_evento_em` (para a componente de recencia) e uma tabela auxiliar de
buckets diarios (`EngajamentoDiario`, um por matricula por dia) para a
componente de frequencia. Um evento novo so precisa:

1. Incrementar (ou criar) o bucket do dia corrente, O(1).
2. Apagar buckets mais antigos que a janela de frequencia, uma query indexada
   que toca no maximo alguns registros por matricula.
3. Somar os buckets restantes (no maximo `janela_frequencia_dias` linhas)
   para obter `soma_pesos_14d`.

O custo por evento fica limitado ao tamanho da janela, nao ao historico
completo, e o MongoDB continua guardando o evento bruto para auditoria e
para casos em que a formula de risco precise ser recalculada do zero
(reprocessamento em lote, fora do caminho quente de ingestao).
"""

import datetime as dt
from dataclasses import dataclass

from pymongo.collection import Collection
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import obter_configuracao
from app.models.orm import EngajamentoDiario, Matricula, Turma
from app.models.schemas import PESOS_EVENTO, EventoComportamentoCriar
from app.services.erros import MatriculaNaoEncontrada
from app.services.risco import calcular_score_risco, faixa_de_score


@dataclass
class ResultadoProcessamentoEvento:
    matricula: Matricula
    faixa_anterior: str
    faixa_nova: str
    dias_sem_atividade: int | None

    @property
    def mudou_de_faixa(self) -> bool:
        return self.faixa_anterior != self.faixa_nova


def _atualizar_bucket_diario(sessao: Session, matricula_id: int, data_evento: dt.date, peso: float) -> None:
    bucket = sessao.execute(
        select(EngajamentoDiario).where(
            EngajamentoDiario.matricula_id == matricula_id,
            EngajamentoDiario.data == data_evento,
        )
    ).scalar_one_or_none()
    if bucket is None:
        sessao.add(EngajamentoDiario(matricula_id=matricula_id, data=data_evento, soma_pesos=peso))
    else:
        bucket.soma_pesos += peso


def _podar_buckets_antigos(sessao: Session, matricula_id: int, data_limite: dt.date) -> None:
    sessao.execute(
        delete(EngajamentoDiario).where(
            EngajamentoDiario.matricula_id == matricula_id,
            EngajamentoDiario.data < data_limite,
        )
    )


def _somar_janela(sessao: Session, matricula_id: int, data_limite: dt.date) -> float:
    total = sessao.execute(
        select(func.coalesce(func.sum(EngajamentoDiario.soma_pesos), 0.0)).where(
            EngajamentoDiario.matricula_id == matricula_id,
            EngajamentoDiario.data >= data_limite,
        )
    ).scalar_one()
    return float(total)


def processar_evento(
    sessao: Session,
    colecao_eventos: Collection,
    evento: EventoComportamentoCriar,
    agora: dt.datetime | None = None,
) -> ResultadoProcessamentoEvento:
    settings = obter_configuracao()
    agora = agora or dt.datetime.now(dt.UTC)

    matricula = sessao.get(Matricula, evento.matricula_id)
    if matricula is None:
        raise MatriculaNaoEncontrada(f"Matricula {evento.matricula_id} nao encontrada")

    turma = sessao.get(Turma, matricula.turma_id)
    timestamp_evento = evento.timestamp or agora
    if timestamp_evento.tzinfo is None:
        # Timestamp sem fuso (ex: vindo de um payload externo sem offset) e
        # tratado como UTC, mesma convencao usada no resto do sistema; sem
        # isso, comparar com `agora` (aware) explode com TypeError.
        timestamp_evento = timestamp_evento.replace(tzinfo=dt.UTC)
    peso = PESOS_EVENTO[evento.tipo]

    colecao_eventos.insert_one(
        {
            "matricula_id": matricula.id,
            "aluno_id": matricula.aluno_id,
            "turma_id": matricula.turma_id,
            "tipo": evento.tipo,
            "peso": peso,
            "timestamp": timestamp_evento,
            "metadados": evento.metadados,
        }
    )

    _atualizar_bucket_diario(sessao, matricula.id, timestamp_evento.date(), peso)
    data_limite = agora.date() - dt.timedelta(days=settings.janela_frequencia_dias - 1)
    _podar_buckets_antigos(sessao, matricula.id, data_limite)
    soma_pesos_janela = _somar_janela(sessao, matricula.id, data_limite)

    if matricula.ultimo_evento_em is None or timestamp_evento >= matricula.ultimo_evento_em:
        matricula.ultimo_evento_em = timestamp_evento
        matricula.ultimo_evento_tipo = evento.tipo

    dias_sem_atividade = (agora.date() - matricula.ultimo_evento_em.date()).days
    dias_sem_atividade = max(dias_sem_atividade, 0)

    faixa_anterior = matricula.faixa_risco
    score = calcular_score_risco(
        dias_sem_atividade=dias_sem_atividade,
        soma_pesos_janela=soma_pesos_janela,
        engajamento_esperado=turma.engajamento_esperado_14d,
        peso_recencia=settings.peso_recencia,
        peso_frequencia=settings.peso_frequencia,
    )
    faixa_nova = faixa_de_score(score)

    matricula.soma_pesos_14d = soma_pesos_janela
    matricula.score_risco = score
    matricula.faixa_risco = faixa_nova

    sessao.commit()
    sessao.refresh(matricula)

    return ResultadoProcessamentoEvento(
        matricula=matricula,
        faixa_anterior=faixa_anterior,
        faixa_nova=faixa_nova,
        dias_sem_atividade=dias_sem_atividade,
    )
