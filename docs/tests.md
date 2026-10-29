# `tests/`: tests automáticos

Se corren con `pytest -q`. No usan red ni API keys: el LLM se simula. La CI de GitHub los
ejecuta en cada push y pull request.

| Archivo | Qué prueba |
|---|---|
| `conftest.py` | Fixtures compartidas: `sample_csv` genera un dataset sintético chico en una carpeta temporal; `settings` arma una configuración sin LLM que escribe en carpetas temporales e ignora tu `.env` |
| `test_sources.py` | Búsqueda sin distinguir acentos ni mayúsculas, `limit` y orden por interacción, `sql()` solo de lectura, `labels()`, y que `ReplaySource` no muestre mensajes futuros |
| `test_clustering.py` | Vectores de norma 1, que dos grupos obvios se separen, que el clustering sea determinístico, y márgenes y términos principales |
| `test_graph.py` | Corrida completa sin LLM (todos los mensajes asignados, proporciones que suman 1, subtópicos que suman su tópico padre); corrida con `StubLLM` (se usan keywords, nombres y reasignaciones del LLM); y que `save_run` escriba todos los archivos |
| `test_metrics.py` | Particiones iguales con nombres distintos dan puntaje perfecto; `level()` recorta paths |
| `test_topic_models.py` | KMeans y LDA devuelven un tópico y una confianza por mensaje y son determinísticos; los outliers van al tópico más cercano con confianza 0; BERTopic arma una jerarquía en la que cada subtópico pertenece a un solo tópico. Este último se saltea si BERTopic no está instalado, como en la CI |
| `test_cli.py` | `foco compare` sin LLM escribe una fila por método y un `eval.json` por celda |

## `StubLLM`

En `test_graph.py`. Reemplaza a `LLM.structured()` con respuestas fijas que tienen la forma
de cada esquema. Para eso lee del prompt los `cluster_id=` y los índices `[n]`. Si se cambia
el formato de los prompts, hay que actualizarlo.

## Para agregar un test

Crear `tests/test_<algo>.py` con funciones `test_*`. Para un test que corra el agente, usar
la fixture `settings` y pasar `llm=StubLLM(settings)` si hace falta simular el LLM.
