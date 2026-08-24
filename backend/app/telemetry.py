import structlog
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sqlalchemy import Engine

from app.config import obter_configuracao

logger = structlog.get_logger(__name__)


def configurar_telemetria(app: FastAPI, engine: Engine) -> None:
    """Liga o tracing distribuido, exportando spans via OTLP/gRPC para o
    Jaeger. Desligado em testes (`otel_habilitado=False`) para nao tentar
    abrir conexao de rede nenhuma durante a suite.
    """
    settings = obter_configuracao()
    if not settings.otel_habilitado:
        logger.info("telemetria_desabilitada")
        return

    provedor = TracerProvider(resource=Resource.create({"service.name": settings.otel_service_name}))
    exportador = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
    provedor.add_span_processor(BatchSpanProcessor(exportador))
    trace.set_tracer_provider(provedor)

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
    PymongoInstrumentor().instrument()
    logger.info("telemetria_configurada", endpoint=settings.otel_exporter_otlp_endpoint)
