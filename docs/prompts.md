# `prompts.py`: prompts del agente

Todos los textos que se le mandan al LLM. Están separados del código para poder iterarlos y
comparar versiones sin tocar la lógica. Hay tres tareas, cada una con un prompt de sistema
(constante) y una función que arma el mensaje del usuario.

| Tarea | Sistema | Mensaje | Respuesta (`schemas.py`) | Lo usa |
|---|---|---|---|---|
| Proponer keywords de búsqueda | `PLAN_SYSTEM` | `plan_user(theme)` | `SearchPlan` | `plan_queries` |
| Nombrar y describir clusters | `LABEL_SYSTEM` | `label_user(theme, parent, clusters)` | `TopicLabels` | `split_topic` → `_label` |
| Reclasificar mensajes dudosos | `ASSIGN_SYSTEM` | `assign_user(topics, tweets)` | `Assignments` | `split_topic` → `_reassign_ambiguous` |

## Qué recibe el LLM en cada caso

- **`label_user`**: la temática general; si son subtópicos, el nombre del tópico padre; y por
  cada cluster su `cluster_id`, tamaño, términos frecuentes y una muestra de mensajes con
  likes y seguidores del autor.
- **`assign_user`**: la lista de tópicos (`cluster_id`, nombre y descripción) y los mensajes
  numerados `[0]`, `[1]`, ... El LLM responde con pares (índice, `cluster_id`).

## Al modificar un prompt

- Cambiar un prompt invalida la caché de esas llamadas (ver [llm.md](llm.md)): la próxima
  corrida vuelve a llamar a la API.
- Comparar con `foco eval` antes y después del cambio.
- Si se cambia el formato de los mensajes (por ejemplo `cluster_id=`), revisar el
  `StubLLM` de `tests/test_graph.py`, que lee ese formato.
- Problema conocido: con modelos locales chicos, `PLAN_SYSTEM` produce keywords con guiones
  bajos (`partidos_políticos`) que no aparecen en los mensajes, y deja afuera subtemas como
  "debate" o "encuesta".
