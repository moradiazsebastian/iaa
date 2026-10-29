# `llm.py`: acceso al LLM

Clase `LLM`: la única puerta de entrada al modelo de lenguaje. El resto del código no sabe
qué proveedor se usa.

## Construcción (`_build`)

Usa `init_chat_model()` de LangChain con `LLM_PROVIDER` y `LLM_MODEL`, más ajustes por
proveedor:

| Proveedor | Ajustes |
|---|---|
| `anthropic` | `max_tokens=16000` y `effort` (de `LLM_EFFORT`). **No** se pasa `temperature`, porque los modelos de Claude actuales la rechazan |
| `ollama` | `temperature=0`, `seed=SEED`, `num_ctx=LLM_NUM_CTX` |
| `openai` | valores por defecto |
| cualquiera | `base_url` si `LLM_BASE_URL` está definido |

Con `LLM_PROVIDER=none` no se crea ningún modelo, y `enabled` es `False`. Los nodos del
grafo revisan `llm.enabled` y usan alternativas sin LLM.

## `structured(schema, system, user) -> instancia de schema`

El único método que usan los nodos. Recibe una clase Pydantic de `schemas.py`, el prompt de
sistema y el mensaje del usuario, y devuelve una instancia validada de esa clase.

Internamente usa `with_structured_output(schema, method="json_schema")`: el proveedor
restringe la respuesta al esquema JSON. Con Claude no hace falta forzar una llamada a una
herramienta, algo que los modelos nuevos no permiten.

## Caché en disco

Antes de llamar al modelo, calcula una clave SHA-256 con proveedor, modelo, effort,
esquema, prompt de sistema y mensaje. Si existe `.cache/llm/<clave>.json`, devuelve esa
respuesta sin llamar a la API.

- **Por qué existe:** Claude no acepta `temperature=0`, así que dos llamadas iguales pueden
  responder distinto. La caché hace que re-ejecutar sobre los mismos datos dé el mismo
  resultado, y además ahorra costo y tiempo.
- **Cuándo se invalida:** si cambia cualquier parte de la clave (por ejemplo, se edita un
  prompt o se cambia de modelo), la clave es otra y se vuelve a llamar.
- **Cómo desactivarla:** `LLM_CACHE=false`, o borrar `.cache/`. `foco repro` la desactiva
  sola para medir la variación real.

## Contadores

`calls` (llamadas reales a la API) y `cache_hits` (respuestas tomadas de la caché). Aparecen
en `config.json` y en el reporte.
