import logging
import sys

import structlog

from app.config import obter_configuracao


def configurar_logging() -> None:
    """Configura saida em JSON estruturado (exceto em desenvolvimento local,
    onde um console renderer legivel ajuda mais do que JSON cru no terminal).
    """
    settings = obter_configuracao()
    processadores_compartilhados = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.ambiente == "desenvolvimento":
        processador_final = structlog.dev.ConsoleRenderer()
    else:
        processador_final = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*processadores_compartilhados, processador_final],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
