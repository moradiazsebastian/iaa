# App web (Vercel)

La app web es una capa encima del agente: una API en Python que envuelve `run_analysis()` y
una interfaz en Next.js. La CLI sigue funcionando igual: nada de lo de abajo la afecta.

```
iaa/
├── src/foco_social/api.py   API (FastAPI): la usa la web, la CLI no
├── api/index.py             entrypoint que busca Vercel; solo importa la API
├── vercel.json              configuración de Vercel (duración, archivos excluidos)
└── web/                     interfaz en Next.js (generada con v0)
```

## Correr la API en local

```bash
pip install -e ".[dev]"          # instala fastapi y uvicorn
uvicorn foco_social.api:app --reload --port 8000
```

Documentación interactiva en http://localhost:8000/docs. Usa la misma configuración que la
CLI (`.env`): proveedor de LLM, dataset, método por defecto.

Para la interfaz en local, Next.js corre en el puerto 3000. La API acepta pedidos de
`http://localhost:3000` (variable `CORS_ORIGINS`, separada por comas).

## Endpoints

### `GET /api/health`
`{"status": "ok", "version": "0.1.0"}`

### `GET /api/options`
Lo que la interfaz puede ofrecer:

```json
{
  "methods": ["kmeans", "lda"],
  "llm_available": true,
  "llm_provider": "anthropic",
  "llm_model": "claude-opus-5-5",
  "dataset": "tweets.csv",
  "dataset_has_labels": true
}
```

`methods` incluye `bertopic` solo si está instalado (en Vercel no lo está).
`llm_available` es `false` si no hay proveedor o falta la API key.

### `POST /api/runs`
Ejecuta el agente. Pedido (solo `theme` es obligatorio):

```json
{
  "theme": "elecciones presidenciales",
  "keywords": null,
  "method": "kmeans",
  "n_topics": 4,
  "n_subtopics": 2,
  "depth": 2,
  "max_tweets": 2000,
  "since": null,
  "until": null,
  "use_llm": true,
  "evaluate": true
}
```

| Campo | Valores | Default |
|---|---|---|
| `keywords` | lista de strings; `null` = las propone el LLM | `null` |
| `method` | `kmeans`, `lda`, `bertopic` | `kmeans` |
| `n_topics` | 2 a 15, o `null` (automático) | `null` |
| `n_subtopics` | 2 a 10, o `null` | `null` |
| `depth` | 1 a 3 | 2 |
| `max_tweets` | 10 a 5000 | 2000 |
| `use_llm` | sin LLM, los nombres son términos frecuentes | `true` |
| `evaluate` | calcula métricas si el dataset tiene etiquetas | `true` |

Respuesta:

```json
{
  "theme": "elecciones presidenciales",
  "method": "kmeans",
  "llm": "claude-opus-5-5",
  "keywords": ["elecciones", "debate", "..."],
  "stats": {"seconds": 24.1, "n_tweets": 289, "llm_calls": 11, "llm_cache_hits": 0},
  "topics": [
    {
      "path": "1", "name": "Debate presidencial", "description": "...",
      "level": 1, "n_tweets": 96, "share_of_parent": 0.33, "share_of_total": 0.33,
      "sample_tweet_ids": ["t00012", "t00187", "t00230"]
    },
    {"path": "1.1", "level": 2, "...": "..."}
  ],
  "assignments": [
    {"id": "t00012", "topic_path": "1.1", "topic": "Debate presidencial",
     "subtopic": "Desempeño de los candidatos", "text": "..."}
  ],
  "metrics": {
    "topics": {"n": 289, "ari": 0.45, "nmi": 0.58, "matched_accuracy": 0.6, "matching": {"...": "..."}},
    "subtopics": {"...": "..."}
  }
}
```

`topics` es una lista plana ordenada por `path`. El árbol se arma con el `path`: `1.2` es
hijo de `1`. `metrics` es `null` si el dataset no tiene etiquetas o si `evaluate` es `false`.

Errores (cuerpo `{"detail": "mensaje"}`):

| Código | Cuándo |
|---|---|
| 422 | pedido inválido (p. ej. `depth` fuera de rango) |
| 404 | ningún mensaje coincide con las keywords |
| 400 | método no instalado (BERTopic en Vercel) |
| 503 | `use_llm: true` pero no hay LLM configurado |

Una corrida con LLM tarda entre segundos y un par de minutos: la interfaz tiene que mostrar
un estado de carga.

## Desplegar en Vercel

1. **Variables de entorno** (Project → Settings → Environment Variables):
   `ANTHROPIC_API_KEY`, y opcionalmente `LLM_MODEL`, `LLM_EFFORT`, `TOPIC_MODEL`.
   Ollama no está disponible en Vercel.
2. **Protección**: activar Deployment Protection (Vercel Authentication o contraseña) antes
   de compartir la URL. Cualquiera con acceso puede disparar llamadas al LLM con tu API key.
3. **Límites**: una función dura como máximo 300 s en el plan Hobby (`maxDuration` en
   `vercel.json`). BERTopic no entra en una función de Vercel (torch pesa ~480 MB).
4. **Archivos**: en Vercel solo `/tmp` es escribible. La API guarda ahí la caché del LLM, que
   se pierde entre ejecuciones. Para guardar el historial de corridas hace falta una base de
   datos (Postgres) o Vercel Blob.
5. **Datos reales**: no se suben al repo. Para usarlos en la app hay que guardarlos en un
   almacenamiento privado (p. ej. Vercel Blob) y apuntar `DATA_PATH` a ellos.

### Cuando exista `web/`

Vercel tiene que construir la interfaz y la API en el mismo proyecto. La opción
recomendada es Vercel Services (beta), configurado en `vercel.json`: un servicio para `web/`
y otro para la API, con `/api/*` dirigido a la API. Esa configuración se agrega junto con el
código de `web/`.
