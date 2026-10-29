# Foco Social

Agente para **detección de tópicos en redes sociales** (X/Twitter). Dada una temática y una
granularidad, busca mensajes relevantes, los agrupa en tópicos y subtópicos, los nombra y
describe con un LLM, y marca cada mensaje con su tópico para calcular qué proporción del
total representa cada uno.

Construido con **LangGraph / LangChain**. El proveedor de LLM es configurable.

## Inicio rápido

Requiere Python 3.10+.

```bash
git clone <url-del-repo> && cd foco-social
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # Windows: copy .env.example .env
```

**Sin API key** (agrupamiento clásico + etiquetas por términos frecuentes):

```bash
foco run --theme "elecciones" --keywords debate,encuesta,fraude,voto,inflacion,candidato --provider none
```

**Con LLM**: completar `ANTHROPIC_API_KEY` en `.env` y:

```bash
foco run --theme "elecciones presidenciales"
```

Ambos usan el dataset sintético de `data/sample/` (ver [data/README.md](data/README.md)).

## Uso

```bash
foco run   --theme "<temática>" [opciones]   # análisis + reporte
foco eval  --theme "<temática>" [opciones]   # análisis + métricas contra etiquetas manuales
foco repro --theme "<temática>" [opciones]   # dos corridas sin caché: ¿cuánto difieren?
foco compare --theme "<temática>" [opciones] # cada método de tópicos, con y sin LLM
foco make-sample                             # regenera el dataset sintético
```

| opción | descripción |
|---|---|
| `--method kmeans\|lda\|bertopic` | método de detección de tópicos (pisa `TOPIC_MODEL`) |
| `--keywords a,b,c` | keywords de búsqueda; si se omite, las propone el LLM a partir de la temática |
| `--topics N` / `--subtopics N` | cantidad de tópicos / subtópicos por tópico (default: automática) |
| `--depth D` | 1 = solo tópicos, 2 = tópicos + subtópicos (default 2) |
| `--max-tweets N` | máximo de mensajes a recuperar (default 2000) |
| `--since` / `--until` | rango de fechas ISO, p. ej. `2026-10-01` |
| `--data PATH` | otro dataset (pisa `DATA_PATH`) |
| `--provider` / `--model` | pisan `LLM_PROVIDER` / `LLM_MODEL` |

Cada ejecución crea `runs/<fecha>-<tipo>-<tema>/` con:

- `report.md`: árbol de tópicos con proporciones, descripciones y mensajes de ejemplo
- `assignments.csv`: tópico asignado a cada mensaje
- `topics.json`, `config.json` (parámetros, keywords, configuración, tiempos, llamadas al LLM), `run.log`
- `eval.json` / `repro.json` según el comando

En Linux/macOS hay atajos en el `Makefile` (`make run THEME="..."`, `make test`, ...).

## Cómo funciona

```
START → plan_queries → retrieve → split_topic ⟲ (mientras queden tópicos por subdividir) → END
```

1. **plan_queries**: el LLM expande la temática en keywords (sinónimos, hashtags, nombres propios).
2. **retrieve**: busca en la fuente de datos (DuckDB sobre CSV/Parquet), priorizando mensajes con más interacción.
3. **split_topic**: para el conjunto de mensajes en la cabeza de la cola:
   - agrupa los mensajes con el método elegido (ver abajo);
   - el LLM **nombra y describe** cada grupo a partir de una muestra (la mitad, los de más
     interacción; la otra mitad, al azar);
   - el LLM **reclasifica solo los mensajes ambiguos** (los que quedan casi a la misma distancia
     de dos centroides);
   - si no se llegó a la profundidad pedida, cada tópico vuelve a la cola para buscar subtópicos.

El LLM nunca ve todos los mensajes: el costo crece con la cantidad de tópicos, no con la de
mensajes. Este diseño responde al riesgo de costo y límites de contexto del proyecto.

### Métodos de detección de tópicos

Se eligen con `TOPIC_MODEL` o `--method`. Los pasos del LLM son los mismos para los tres.

| Método | Cómo agrupa | Instalación |
|---|---|---|
| `kmeans` (default) | TF-IDF (o embeddings) + KMeans | incluido |
| `lda` | Latent Dirichlet Allocation sobre conteo de palabras. Rinde peor en textos cortos | incluido |
| `bertopic` | embeddings multilingües → UMAP → HDBSCAN. Los tópicos finos que encuentra se unen jerárquicamente en tópicos de nivel 1 y quedan como subtópicos. Los mensajes que no encajan en ningún tópico (outliers) van al tópico más cercano y son los primeros que revisa el LLM | `pip install -e ".[bertopic]"` (~2 GB) |

`foco compare` corre la grilla método × (con / sin LLM) con las mismas keywords y los mismos
mensajes, y guarda una tabla en `runs/<id>/results.md`. Ejemplo sin LLM sobre el dataset
sintético (`--topics 4 --subtopics 2`):

| método | ARI tópicos | ARI subtópicos | segundos |
|---|---|---|---|
| kmeans | 0.22 | 0.26 | 0.3 |
| lda | 0.16 | 0.21 | 1.6 |
| bertopic | 0.27 | 0.36 | 18 |

El dataset sintético es chico y artificial: la comparación que importa es sobre los datos
etiquetados reales.

### Fuentes de datos

Todas implementan `TweetSource.search(keywords, since, until, limit)` (`src/foco_social/sources/`):

- `StaticSource`: dataset estático; también expone `sql()` de solo lectura.
- `ReplaySource`: simula tiempo real reproduciendo el dataset por timestamp (`advance()` mueve el reloj).
- Para la API de X: implementar otra clase con el mismo método `search`.

## Evaluación

- `foco eval` compara contra las columnas `topic` / `subtopic` del dataset:
  **ARI** y **NMI** (acuerdo entre particiones, sin importar los nombres) y **matched_accuracy**
  (emparejando 1 a 1 tópicos predichos y reales con el algoritmo húngaro).
- `foco repro` corre dos veces **sin caché** y reporta el ARI entre ambas corridas. Es la métrica
  para el umbral de tolerancia de reproducibilidad.

Referencia sin LLM sobre el dataset sintético (`--topics 4 --subtopics 2`): ARI de tópicos ≈ 0.22,
matched_accuracy ≈ 0.59. El LLM debería superar esta línea de base.

## Configuración (`.env`)

| variable | default | |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | `anthropic`, `openai`, `ollama` o `none` |
| `LLM_MODEL` | `claude-opus-5-5` | cualquier modelo del proveedor elegido |
| `LLM_EFFORT` | `low` | esfuerzo de razonamiento (solo Anthropic) |
| `LLM_CACHE` | `true` | caché en disco de respuestas del LLM (`.cache/`) |
| `DATA_PATH` | `data/sample/tweets.csv` | |
| `TOPIC_MODEL` | `kmeans` | `kmeans`, `lda` o `bertopic` |
| `EMBEDDINGS` | `tfidf` | solo para `kmeans`; `sentence-transformers` requiere `pip install -e ".[embeddings]"` |
| `MAX_LLM_REASSIGN` | `120` | máximo de mensajes dudosos u outliers que reclasifica el LLM por nivel |
| `SEED` | `42` | |
| `LANGSMITH_TRACING` | `false` | opcional: trazas en LangSmith con `LANGSMITH_API_KEY` |

Para OpenAI: `pip install -e ".[openai]"`.

### Modelo local con Ollama

`.env` no se sube al repo, así que cada integrante puede usar su propio proveedor sin
afectar a los demás.

```bash
pip install -e ".[ollama]"
ollama pull qwen2.5:7b
```

En tu `.env`:

```
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
```

O para una sola corrida, sin tocar `.env`: `foco run --theme "..." --provider ollama --model qwen2.5:7b`.

Con Ollama se usan temperatura 0 y la semilla `SEED`. `LLM_NUM_CTX` (default 16384) amplía la
ventana de contexto, porque la de Ollama por defecto es demasiado chica para los prompts de etiquetado.
`LLM_BASE_URL` sirve si el servidor corre en otro puerto u otra máquina. Usá un modelo que
soporte salida estructurada (JSON schema), como `qwen2.5`, `llama3.1` o `mistral-nemo`.

**Reproducibilidad.** Los modelos de Claude actuales no aceptan `temperature`, así que no se
puede fijar en 0. Las corridas se hacen repetibles con semillas fijas en el clustering y el
muestreo, y con la caché del LLM: la misma consulta devuelve la misma respuesta guardada.
Si se cambia un prompt o el modelo, la clave de la caché cambia y se vuelve a llamar a la API.

## Estructura

Ver [docs/](docs/README.md) para una explicación de cada archivo.

```
src/foco_social/
  cli.py            comandos foco run | eval | repro | make-sample
  runner.py         ejecuta el grafo y guarda resultados
  config.py         configuración (.env)
  llm.py            LLM vía LangChain + salida estructurada + caché
  prompts.py        prompts del agente
  schemas.py        modelos de datos y esquemas de salida del LLM
  clustering.py     vectorización + KMeans
  topic_models.py   métodos de tópicos intercambiables (KMeans, LDA, BERTopic)
  graph/            estado, nodos y armado del grafo LangGraph
  sources/          fuentes de datos (estática, replay)
  evaluation/       métricas y generador de datos sintéticos
tests/              tests sin red (el LLM se simula)
data/sample/        dataset sintético de ejemplo
```

## Desarrollo

```bash
pytest -q
ruff check src tests && ruff format src tests
```

La CI (GitHub Actions) corre lint, tests y una evaluación completa sin LLM. No necesita secretos.
