# `graph/`: el agente en LangGraph

```
START → plan_queries → retrieve → split_topic ⟲ → END
```

`split_topic` se repite mientras haya tópicos en la cola por subdividir. Cada nodo recibe el
estado completo y devuelve **solo las claves que cambia**: LangGraph las combina con el estado.

## `state.py`: el estado

**`AgentState`**: diccionario que recorre el grafo.

| Clave | La define | Contenido |
|---|---|---|
| `theme`, `keywords`, `n_topics`, `n_subtopics`, `depth`, `max_tweets`, `since`, `until` | el usuario | parámetros de entrada |
| `keywords` | `plan_queries` | si el usuario no las dio |
| `tweets` | `retrieve` | `{id: Tweet}` con todos los mensajes recuperados |
| `queue` | `retrieve`, `split_topic` | conjuntos de mensajes pendientes de subdividir |
| `topics` | `split_topic` | lista acumulada de `Topic` |
| `assignments` | `retrieve`, `split_topic` | `{tweet_id: path}`; empieza en `""` y se va haciendo más específico |
| `presplit` | `split_topic` | `{tweet_id: subtópico}` ya calculado por BERTopic en el nivel 1; vacío con otros métodos |

**`PendingSplit`**: un elemento de la cola. `path` (`""` es la raíz), `name` (nombre del tópico
padre), `tweet_ids` y `level` (el nivel de los tópicos que se van a generar).

## `nodes.py`: los pasos

Clase `Nodes`. Recibe la fuente, el LLM y la configuración, y sus métodos son los nodos.
Los parámetros del constructor ajustan el comportamiento:

| Parámetro | Default | Efecto |
|---|---|---|
| `min_tweets_to_split` | 12 | con menos mensajes, un tópico no se subdivide |
| `samples_per_cluster` | 8 | mensajes de ejemplo que ve el LLM por cluster |
| `ambiguous_quantile` | 0.15 | proporción de mensajes que se consideran dudosos |
| `assign_batch_size` | 40 | mensajes por llamada de reclasificación |

El tope de mensajes que revisa el LLM por nivel es `MAX_LLM_REASSIGN` (configuración).

### `plan_queries`
Si el usuario pasó `--keywords`, no hace nada. Si no, llama a `plan_keywords(theme, llm)`:
parte la temática por comas y le pide al LLM más keywords (`SearchPlan`). Sin LLM, usa solo la
temática. `plan_keywords` es una función suelta para que `foco compare` calcule las keywords
una sola vez y las comparta entre todas las celdas.

### `retrieve`
Llama a `source.search()`. Pone a todos los mensajes en la cola como un único elemento raíz.
Falla si no encuentra nada.

### `split_topic`
Toma el primer elemento de la cola y:

1. Si tiene menos de `min_tweets_to_split` mensajes, lo descarta (queda como hoja).
2. Agrupa con `fit_topics` (el método de `TOPIC_MODEL`; ver [topic_models.md](topic_models.md)).
   Usa `n_topics` en el nivel 1 y `n_subtopics` en los siguientes. Si BERTopic ya calculó los
   subtópicos de estos mensajes (`presplit`), usa `fit_presplit` en lugar de volver a ajustar.
3. **`_label`**: el LLM nombra y describe cada cluster. Sin LLM, el nombre son los 3 términos
   principales.
4. **`_reassign_ambiguous`**: el LLM reclasifica los mensajes con menor `confidence`: el 15%
   menos seguro, más todos los outliers (confianza 0), hasta `MAX_LLM_REASSIGN`.
5. Numera los clusters por tamaño (el más grande es `.1`), crea los `Topic` y actualiza
   `assignments`.
6. Si no se llegó a `depth`, encola cada tópico nuevo para buscar sus subtópicos.

### Auxiliares
- **`_sample`**: la muestra para el LLM es mitad mensajes con más interacción y mitad al
  azar, para no sesgar hacia lo viral. El azar usa una semilla derivada del `path`, así que
  es reproducible.
- **`_format`**: cómo ve el LLM cada mensaje: `[likes, seguidores del autor] texto`.
- **`_top_by_engagement`**: los mensajes de ejemplo del reporte.

## `build.py`: el armado

`build_graph(source, llm, settings)` registra los nodos, conecta las aristas y compila.
`_route` decide después de `retrieve` y de cada `split_topic`: si la cola tiene elementos,
vuelve a `split_topic`; si no, termina.

Para ver el grafo:

```python
graph.get_graph().draw_mermaid()
```

## Para agregar un paso

1. Escribir el método en `Nodes`, que reciba `state` y devuelva un `dict` con las claves que cambia.
2. Si agrega claves nuevas, declararlas en `AgentState`.
3. Registrarlo en `build.py` con `add_node` y conectarlo con `add_edge` / `add_conditional_edges`.
