from fastapi import APIRouter, Depends, status

from app.config import Settings, obter_configuracao
from app.messaging.producer import ProdutorEventos
from app.models.schemas import EventoComportamentoCriar

router = APIRouter(prefix="/eventos", tags=["eventos"])

_produtor_singleton: ProdutorEventos | None = None


def obter_produtor_eventos(settings: Settings = Depends(obter_configuracao)) -> ProdutorEventos:
    """Instancia o produtor sob demanda: a maioria das rotas da API nunca usa
    Kafka, entao nao faz sentido abrir uma conexao com o broker no startup
    so por causa deste unico endpoint de conveniencia.
    """
    global _produtor_singleton
    if _produtor_singleton is None:
        _produtor_singleton = ProdutorEventos(settings.kafka_bootstrap_servers)
    return _produtor_singleton


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def publicar_evento(
    evento: EventoComportamentoCriar,
    settings: Settings = Depends(obter_configuracao),
    produtor: ProdutorEventos = Depends(obter_produtor_eventos),
) -> dict:
    """Endpoint de conveniencia para publicar um evento manualmente (testes,
    demonstracao). Em producao o volume real chega pelo simulador/plataforma
    publicando direto no topico; o processamento em si so acontece quando o
    worker consumidor consome a mensagem, por isso o 202 (aceito, nao processado).
    """
    produtor.publicar(
        settings.kafka_topico_eventos,
        chave=str(evento.matricula_id),
        valor=evento.model_dump(),
    )
    return {"status": "aceito"}
