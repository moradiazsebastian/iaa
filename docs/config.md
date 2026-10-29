# `config.py`: configuración

Define `Settings` con `pydantic-settings`. Cada campo se lee de una variable de entorno con el
mismo nombre en mayúsculas (`llm_model` ← `LLM_MODEL`) o del archivo `.env`. Si no existe,
toma el valor por defecto.

`.env` no se sube al repositorio, así que cada integrante puede usar su propio proveedor,
modelo o dataset sin afectar a los demás. `.env.example` es la plantilla versionada.

## Campos

| Campo | Default | Para qué sirve |
|---|---|---|
| `llm_provider` | `anthropic` | `anthropic`, `openai`, `ollama` o `none` (sin LLM) |
| `llm_model` | `claude-opus-5-5` | nombre del modelo en el proveedor |
| `llm_effort` | `low` | esfuerzo de razonamiento; solo lo usa Anthropic |
| `llm_cache` | `True` | guardar las respuestas del LLM en disco (ver [llm.md](llm.md)) |
| `llm_base_url` | `None` | URL del servidor, p. ej. Ollama en otra máquina |
| `llm_num_ctx` | `16384` | ventana de contexto para Ollama |
| `data_path` | `data/sample/tweets.csv` | dataset a analizar |
| `topic_model` | `kmeans` | `kmeans`, `lda` o `bertopic` (ver [topic_models.md](topic_models.md)) |
| `embeddings` | `tfidf` | `tfidf` o `sentence-transformers`; solo para `kmeans` |
| `max_llm_reassign` | `120` | máximo de mensajes dudosos u outliers que reclasifica el LLM por nivel |
| `seed` | `42` | semilla del clustering, del muestreo y de Ollama |
| `runs_dir` | `runs` | dónde se guardan los resultados |
| `cache_dir` | `.cache` | dónde se guarda la caché del LLM |

## `get_settings(**overrides)`

Crea `Settings` pisando solo los valores que no sean `None`. La CLI la usa para que una
opción como `--provider` tenga prioridad sobre `.env` solo cuando se la pasa.

## Para agregar una opción

1. Agregar el campo con su tipo y default en `Settings`.
2. Documentarlo en `.env.example`.
3. Usarlo desde `settings.<campo>` donde haga falta.
