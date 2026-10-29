# Documentación del código

Guía de qué hace cada archivo Python del proyecto. Para instalar y ejecutar, ver el
[README principal](../README.md).

## Recorrido de una ejecución

```
foco run --theme "..."                         cli.py
   └─ run_analysis()                           runner.py
        ├─ Settings (.env)                     config.py
        ├─ StaticSource (datos)                sources/
        ├─ LLM (LangChain + caché)             llm.py, prompts.py, schemas.py
        └─ grafo LangGraph                     graph/
             plan_queries → retrieve → split_topic ⟲
                                          └─ fit_topics        topic_models.py
                                               (KMeans / LDA / BERTopic, usa clustering.py)
   └─ save_run() → runs/<id>/
foco eval / repro / compare → métricas         evaluation/metrics.py
```

## Índice

| Archivo | Qué hace | Doc |
|---|---|---|
| `cli.py` | Comandos `foco run`, `eval`, `repro`, `compare` y `make-sample` | [cli.md](cli.md) |
| `runner.py` | Ejecuta el grafo de punta a punta y guarda los resultados | [runner.md](runner.md) |
| `config.py` | Configuración leída de `.env` | [config.md](config.md) |
| `llm.py` | Acceso al LLM con salida estructurada y caché en disco | [llm.md](llm.md) |
| `prompts.py` | Textos de los prompts | [prompts.md](prompts.md) |
| `schemas.py` | Modelos de datos y esquemas de respuesta del LLM | [schemas.md](schemas.md) |
| `topic_models.py` | Métodos de tópicos intercambiables: KMeans, LDA, BERTopic | [topic_models.md](topic_models.md) |
| `clustering.py` | Vectorización (TF-IDF / embeddings) y KMeans | [clustering.md](clustering.md) |
| `graph/state.py`, `graph/nodes.py`, `graph/build.py` | El agente en LangGraph | [graph.md](graph.md) |
| `sources/base.py`, `sources/static.py`, `sources/replay.py` | De dónde salen los mensajes | [sources.md](sources.md) |
| `evaluation/metrics.py`, `evaluation/synthetic.py` | Métricas y dataset sintético | [evaluation.md](evaluation.md) |
| `tests/*.py` | Tests automáticos | [tests.md](tests.md) |

Todo el código está en `src/foco_social/`. Los `__init__.py` solo exponen los nombres
públicos de cada paquete (por ejemplo `from foco_social.sources import StaticSource`).

## ¿Dónde toco si quiero...?

| Quiero... | Archivo |
|---|---|
| mejorar las keywords, los nombres de tópicos o la reasignación | `prompts.py` |
| agregar un paso al agente | `graph/nodes.py` + `graph/build.py` |
| usar otro método de tópicos | `TOPIC_MODEL` en `.env`, o `--method` |
| agregar un método de tópicos | `topic_models.py` |
| comparar métodos | `foco compare` |
| conectar la API de X u otra fuente | nueva clase en `sources/` |
| agregar una métrica | `evaluation/metrics.py` + `cmd_eval` en `cli.py` |
| agregar una opción de configuración | `config.py` + `.env.example` |
| agregar un comando | `cli.py` |
