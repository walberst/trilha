from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracao da aplicacao, lida de variaveis de ambiente.

    Os defaults apontam para os nomes de servico do docker-compose, para que
    `docker compose up` funcione sem precisar de um .env preenchido.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ambiente: str = "desenvolvimento"

    database_url: str = "postgresql+psycopg2://trilha:trilha@postgres:5432/trilha"

    mongo_url: str = "mongodb://mongo:27017"
    mongo_database: str = "trilha_eventos"

    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topico_eventos: str = "trilha.eventos-comportamento"
    kafka_topico_alertas: str = "trilha.alertas-risco"
    kafka_group_id_consumidor: str = "trilha-consumidor-eventos"
    kafka_group_id_alertas: str = "trilha-relay-alertas"

    otel_exporter_otlp_endpoint: str = "jaeger:4317"
    otel_service_name: str = "trilha-api"
    otel_habilitado: bool = True

    kafka_habilitado: bool = True

    # Janela usada no calculo de frequencia do score de risco, em dias.
    janela_frequencia_dias: int = 14

    # Pesos da media ponderada entre recencia e frequencia na formula de risco.
    peso_recencia: float = 0.5
    peso_frequencia: float = 0.5

    # Intervalo entre eventos simulados pelo produtor de demonstracao, em segundos.
    simulador_intervalo_segundos: float = 2.0


@lru_cache
def obter_configuracao() -> Settings:
    return Settings()
