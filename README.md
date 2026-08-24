# Trilha

Deteccao antecipada de risco de evasao em cursos online.

## O problema

Plataforma de curso online descobre que um aluno vai desistir quando ja e
tarde demais: o certificado de conclusao caiu, o boleto do proximo modulo
nao foi pago, ou o professor so percebe o sumico quando alguem pergunta "cade
o Fulano?" numa live. O sinal de alerta existia semanas antes, espalhado em
login, video assistido, prova concluida, post no forum, so que ninguem estava
olhando para ele de forma agregada.

O Trilha ingere esse comportamento em fluxo continuo, calcula um score de
risco de evasao por matricula (aluno + turma) e avisa o professor no momento
em que o risco sobe de faixa, antes do abandono virar estatistica.

## Como o risco e calculado

O score combina duas componentes independentes, cada uma numa escala de 0
(sem risco) a 100 (risco maximo):

**Recencia.** Ha quantos dias o aluno nao gera nenhum evento. Usa uma funcao
em degraus, nao uma reta continua, porque a diferenca entre "sumiu ha 2 dias"
e "sumiu ha 6 dias" quase nao importa na pratica, mas cruzar a marca de uma ou
duas semanas sem aparecer e o que de fato indica risco de abandono:

| Dias sem nenhum evento | Pontuacao |
|---|---|
| 0 a 2 | 0 |
| 3 a 6 | 25 |
| 7 a 13 | 55 |
| 14 a 20 | 80 |
| 21 ou mais (ou nunca teve evento) | 100 |

**Frequencia.** Quanto o aluno engajou nos ultimos 14 dias comparado com o
que se espera de um aluno saudavel naquela turma. Cada tipo de evento tem um
peso (prova concluida pesa mais que um login solto), e cada turma define um
`engajamento_esperado_14d` (soma de pesos esperada num aluno ativo). A
pontuacao de frequencia e `100 * (1 - soma_pesos_janela / esperado)`,
zerada quando o aluno atinge ou supera o esperado:

| Tipo de evento | Peso |
|---|---|
| login | 1 |
| video_assistido | 2 |
| post_forum | 3 |
| prova_concluida | 5 |

Isso pega o caso que a recencia sozinha nao pegaria: um aluno que loga todo
dia mas nunca assiste aula nem faz prova parece ativo pela recencia, mas o
engajamento real esta baixo.

O score final e a media ponderada das duas componentes
(`peso_recencia=0.5`, `peso_frequencia=0.5` por padrao, configuravel via
env var), arredondada em duas casas. As faixas:

- `0` a `39,9` -> **baixo risco**
- `40` a `69,9` -> **medio risco**
- `70` a `100` -> **alto risco**

Pesos iguais foram a escolha inicial porque nenhuma das duas componentes
sozinha conta a historia toda: um aluno pode ter feito login ontem (recencia
zerada) mas estar semanas sem tocar em prova, e um aluno pode ter feito uma
maratona de estudos ha 10 dias (frequencia boa) e sumido desde entao. A
formula, as faixas e os pesos ficam centralizados em `backend/app/services/risco.py`
e `backend/app/config.py`, e o motivo de cada escolha esta comentado no
proprio codigo.

### Recalculo incremental, sem reprocessar o historico

A ingestao de eventos e continua (via Kafka) e o volume bruto guardado no
MongoDB so cresce. Reprocessar o historico inteiro de um aluno a cada evento
novo pra recalcular o score seria cada vez mais caro conforme o curso avanca.

Em vez disso, cada matricula guarda um estado incremental no Postgres:

- `ultimo_evento_em`, atualizado direto (O(1)) a cada evento, usado na
  componente de recencia.
- Uma tabela auxiliar `engajamentos_diarios`, um bucket por matricula por
  dia. Um evento novo incrementa (ou cria) o bucket do dia corrente, os
  buckets fora da janela de 14 dias sao apagados (query indexada, poucas
  linhas), e a soma de frequencia usa so os buckets restantes.

O custo por evento fica limitado ao tamanho da janela de frequencia (no
maximo `janela_frequencia_dias` linhas por matricula), nunca ao historico
completo. O MongoDB continua guardando o evento bruto para auditoria e para
um eventual reprocessamento em lote, que roda fora do caminho quente de
ingestao.

## Arquitetura

```
        publica eventos              consome e agrega            consulta REST
alunos ------------------> Kafka --------------------> Postgres <--------------- painel
(simulador)     topico eventos                          MongoDB      professor
                                          |                                ^
                                          | cruzou limiar de faixa         |
                                          v                                |
                                     Kafka topico alertas ---> relay (na API) --> WebSocket
```

Tres processos, um unico topico de dominio dividido em duas responsabilidades:

- **simulator**: simula a plataforma de curso publicando eventos de alunos
  matriculados no topico `trilha.eventos-comportamento`.
- **worker** (`app.messaging.consumer_eventos`): consome o topico de
  eventos, grava o evento bruto no MongoDB, atualiza o estado incremental e
  recalcula o score no Postgres. Quando a faixa de risco de uma matricula
  muda, publica um alerta no topico `trilha.alertas-risco`.
- **api**: expoe os endpoints REST e o WebSocket. No proprio processo, uma
  thread consome o topico de alertas e repassa cada um para as conexoes
  WebSocket abertas naquela turma. Usar Kafka de novo para esse relay (em vez
  de abrir uma dependencia nova so pra pub/sub) evita adicionar Redis ao
  projeto so para empurrar uma notificacao que ja nasceu dentro do Kafka.

Rodar o worker separado da API significa que a ingestao de eventos escala e
falha independente do processo que atende requisicao HTTP/WebSocket.

## Stack

- **Backend**: Python + FastAPI, SQLAlchemy 2.0, Pydantic v2.
- **Banco relacional**: PostgreSQL (cursos, turmas, alunos, matriculas, score
  de risco).
- **Banco nao relacional**: MongoDB (eventos brutos de comportamento).
- **Mensageria**: Kafka (modo KRaft, sem Zookeeper).
- **Tempo real**: WebSocket nativo do FastAPI.
- **Frontend**: Vue 3 (painel do professor + tela de detalhe do aluno).
- **Observabilidade**: OpenTelemetry exportando para Jaeger (tracing),
  structlog (logs estruturados), Prometheus (metricas em `/metrics`).
- **Testes**: pytest, unitarios (formula de risco, gerenciador de WebSocket) e
  de integracao (endpoints da API, processamento de evento de ponta a ponta).

## Como rodar

Banco sobe limpo por padrao:

```bash
docker compose up --build
```

Isso sobe Postgres, MongoDB, Kafka, Jaeger, Prometheus, a API (`localhost:8000`),
o worker de agregacao, o simulador de eventos e o frontend (`localhost:5173`).
Sem nenhum aluno cadastrado ainda, so a estrutura de tabelas criada.

Para ja ter dados de demonstracao (cursos, turmas, alunos e um historico de
eventos variado, cobrindo as tres faixas de risco), rode o seed depois que a
API estiver de pe:

```bash
make seed
# equivalente a:
docker compose exec api python -m scripts.seed
```

O seed e idempotente na pratica: se ja existir algum curso, ele aborta sem
duplicar nada. Depois de rodar, abra `http://localhost:5173/turmas/1` para ver
o painel do professor da primeira turma.

Links uteis depois do `docker compose up`:

- API: `http://localhost:8000` (docs automaticas em `/docs`)
- Painel do professor: `http://localhost:5173`
- Jaeger (tracing): `http://localhost:16686`
- Prometheus: `http://localhost:9090`

### Rodando sem Docker

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate  # ou source .venv/bin/activate no Linux/Mac
pip install -r requirements-dev.txt
pytest
```

Os testes usam SQLite em memoria e mongomock no lugar do Postgres/MongoDB
reais (ver `tests/conftest.py`), entao rodam sem nenhuma infraestrutura
externa. `requirements-drivers.txt` (psycopg2 e confluent-kafka) so entra na
imagem Docker, ja que sao drivers nativos usados apenas contra os bancos e o
Kafka de verdade.

## Testes e CI

```bash
make test   # pytest com cobertura
make lint   # ruff check + ruff format --check
```

O workflow em `.github/workflows/ci.yml` roda lint, testes e build das
imagens Docker (API e worker) a cada push/PR na `main`.

## Endpoints principais

- `GET /turmas/{turma_id}/alunos` - lista paginada de alunos da turma,
  ordenavel por `risco`, `nome` ou `ultimo_evento` (query params `pagina`,
  `tamanho_pagina`, `ordenar_por`, `direcao`). E o endpoint que alimenta o
  painel do professor.
- `GET /matriculas/{matricula_id}` - detalhe de uma matricula: score,
  componentes de recencia/frequencia, ultimo evento.
- `POST /matriculas` - matricula um aluno numa turma (409 se ja matriculado).
- `POST /eventos` - publica um evento de comportamento manualmente no Kafka,
  util para testar o pipeline sem esperar o simulador.
- `WS /ws/turmas/{turma_id}` - canal de atualizacao de risco em tempo real.
- `GET /health` e `GET /health/ready` - liveness e readiness.
- `GET /metrics` - metricas Prometheus.

Erros de negocio (recurso nao encontrado, matricula duplicada) voltam com
`{"detalhe": "...", "codigo": "..."}` e o status HTTP adequado, nao um 500
generico.
