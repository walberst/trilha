import time

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

requisicoes_total = Counter(
    "trilha_http_requisicoes_total",
    "Total de requisicoes HTTP recebidas pela API",
    ["metodo", "rota", "status"],
)

duracao_requisicao_segundos = Histogram(
    "trilha_http_duracao_requisicao_segundos",
    "Duracao das requisicoes HTTP em segundos",
    ["metodo", "rota"],
)

eventos_processados_total = Counter(
    "trilha_eventos_processados_total",
    "Total de eventos de comportamento processados pelo consumidor Kafka",
    ["tipo"],
)

alertas_risco_total = Counter(
    "trilha_alertas_risco_total",
    "Total de vezes que a faixa de risco de uma matricula mudou",
    ["faixa_anterior", "faixa_nova"],
)


class MetricasMiddleware(BaseHTTPMiddleware):
    """Middleware simples de metricas HTTP.

    Usa `request.scope["route"]` (quando disponivel) em vez do path cru para
    nao explodir a cardinalidade das metricas com IDs numericos na URL.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        inicio = time.perf_counter()
        resposta = await call_next(request)
        duracao = time.perf_counter() - inicio

        rota = request.scope.get("route")
        rota_template = rota.path if rota is not None else request.url.path

        requisicoes_total.labels(
            metodo=request.method, rota=rota_template, status=resposta.status_code
        ).inc()
        duracao_requisicao_segundos.labels(metodo=request.method, rota=rota_template).observe(
            duracao
        )
        return resposta
