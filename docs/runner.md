# `runner.py`: ejecución y resultados

Conecta todas las piezas: arma la fuente de datos, el LLM y el grafo, lo ejecuta y escribe
los archivos de salida. Es la función a usar para correr el agente desde Python, por ejemplo
en un notebook o en una futura interfaz web:

```python
from foco_social.config import get_settings
from foco_social.runner import run_analysis

result = run_analysis(get_settings(), theme="elecciones", n_topics=5, depth=2)
result.assignments_frame().head()
```

## `run_analysis(settings, theme, ...) -> AnalysisResult`

1. Crea `StaticSource(settings.data_path)` y `LLM(settings)`, salvo que se pasen otros
   (los tests pasan un LLM simulado).
2. Arma el grafo con `build_graph()` y lo ejecuta con `graph.invoke(params)`.
   `recursion_limit=500` permite que `split_topic` se repita muchas veces. El límite por
   defecto de LangGraph es 25 pasos.
3. Mide el tiempo y devuelve un `AnalysisResult`.

Parámetros: `keywords` (si se omite, las genera el LLM), `n_topics` / `n_subtopics`
(`None` = automático), `depth`, `max_tweets`, `since` / `until`, `source`, `llm`.

## `AnalysisResult`

| Campo | Contenido |
|---|---|
| `params` | parámetros de la corrida |
| `keywords` | keywords usadas en la búsqueda |
| `topics` | lista de `Topic`, ordenada por path (`1`, `1.1`, `1.2`, `2`, ...) |
| `assignments` | `{tweet_id: path}` con el tópico más específico de cada mensaje |
| `texts` | `{tweet_id: texto}` |
| `stats` | segundos, cantidad de mensajes, llamadas al LLM y aciertos de caché |

- `topic_names()` devuelve `{path: nombre}`.
- `assignments_frame()` devuelve un DataFrame con `id`, `topic_path`, `topic`, `subtopic` y `text`.

## `save_run(result, settings, run_dir)`

Escribe en `run_dir`:

| Archivo | Contenido |
|---|---|
| `config.json` | parámetros, keywords, estadísticas y configuración completa |
| `topics.json` | todos los tópicos con proporciones y mensajes de ejemplo |
| `assignments.csv` | un mensaje por fila con su tópico y subtópico |
| `report.md` | reporte legible (lo genera `render_report`) |

## `render_report(result)`

Genera el árbol de tópicos en Markdown: nombre, cantidad de mensajes, porcentaje del total,
porcentaje del nivel superior, descripción y hasta tres mensajes de ejemplo (los de más
interacción).
