# `schemas.py`: modelos de datos

Clases Pydantic en tres grupos.

## Datos de entrada

**`Tweet`**: un mensaje. Campos `id`, `created_at`, `author`, `author_followers`, `text`,
`likes` y `retweets`. Lo crean las fuentes de datos (`sources/`).

## Respuestas del LLM

Se pasan a `LLM.structured()`, que obliga al modelo a responder con esa forma. Las
descripciones de los campos (`Field(description=...)`) forman parte del esquema que ve el
modelo, así que funcionan como instrucciones adicionales.

| Clase | Contenido | Tarea |
|---|---|---|
| `SearchPlan` | `keywords: list[str]` | proponer keywords |
| `TopicLabel` / `TopicLabels` | `cluster_id`, `name`, `description` por cluster | nombrar clusters |
| `Assignment` / `Assignments` | `tweet_index`, `cluster_id` por mensaje | reclasificar mensajes dudosos |

## Resultado

**`Topic`**: un tópico o subtópico del resultado.

| Campo | Ejemplo | Significado |
|---|---|---|
| `path` | `"2.1"` | posición en el árbol: subtópico 1 del tópico 2 |
| `name`, `description` | | generados por el LLM, o por términos TF-IDF si no hay LLM |
| `level` | `2` | 1 = tópico, 2 = subtópico, ... |
| `n_tweets` | `40` | mensajes asignados |
| `share_of_parent` | `0.5` | proporción respecto del tópico padre |
| `share_of_total` | `0.12` | proporción respecto de todos los mensajes analizados |
| `sample_tweet_ids` | | hasta 3 mensajes con más interacción |
