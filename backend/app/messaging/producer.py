import json


class ProdutorEventos:
    """Wrapper fino sobre o Producer do confluent-kafka.

    O import da lib fica dentro do metodo em vez do topo do modulo: ela exige
    o binario nativo librdkafka, e nada no caminho de testes (que roda contra
    SQLite/mongomock, sem broker nenhum) precisa instanciar um produtor de
    verdade. Isso deixa o modulo importavel em qualquer ambiente.
    """

    def __init__(self, bootstrap_servers: str) -> None:
        from confluent_kafka import Producer

        self._producer = Producer({"bootstrap.servers": bootstrap_servers})

    def publicar(self, topico: str, chave: str, valor: dict) -> None:
        self._producer.produce(
            topico, key=chave.encode("utf-8"), value=json.dumps(valor, default=str).encode("utf-8")
        )
        self._producer.poll(0)

    def flush(self, timeout: float = 5.0) -> None:
        self._producer.flush(timeout)
