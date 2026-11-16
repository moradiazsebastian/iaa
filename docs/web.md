# App web (Vercel)

La app web es una capa encima del agente: una API en Python que envuelve `run_analysis()` y
una interfaz en Next.js. La CLI sigue funcionando igual: nada de lo de abajo la afecta.

```
iaa/
├── src/foco_social/api.py   API (FastAPI): la usa la web, la CLI no
├── api/index.py             entrypoint de la API en Vercel; solo importa la API
├── web/                     interfaz en Next.js 16 (pnpm)
│   ├── src/app/             layout, página y estilos
│   ├── src/components/      formulario, resultados, árbol de temas, tabla, métricas
│   └── src/lib/             cliente de la API (api.ts), tipos y formatos
└── vercel.json              dos servicios: "web" (web/) y "api" (Python); /api/* va a la API
```

## Correr la app completa en local

Hacen falta dos terminales: la API en el puerto 8000 y la web en el 3000.

```bash
# Terminal 1: API (desde la raíz del repo)
pip install -e ".[dev]"
uvicorn foco_social.api:app --reload --port 8000

# Terminal 2: web
cd web
corepack enable            # una vez; o usar "npx pnpm@10.34.3" en lugar de "pnpm"
pnpm install
pnpm dev
```

Abrir http://localhost:3000. En desarrollo, Next.js reenvía `/api/*` a
`http://127.0.0.1:8000` (`web/next.config.ts`), así que no hace falta configurar CORS.
La documentación interactiva de la API está en http://localhost:8000/docs.

La API usa la misma configuración que la CLI (`.env`): proveedor de LLM, dataset y método por
defecto. Para apuntar la web a una API en otro dominio, definir `NEXT_PUBLIC_API_BASE_URL` y
agregar ese origen a `CORS_ORIGINS` en la API.

Antes de abrir un pull request que toque `web/`: `pnpm lint && pnpm build`. La CI lo corre
(`.github/workflows/web.yml`) solo cuando cambia algo en `web/`.

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

### Cómo se sirven la web y la API

`vercel.json` usa Vercel Services (beta): el servicio `web` construye `web/` con Next.js y
el servicio `api` sirve la app de FastAPI. Las reglas de `rewrites` mandan `/api/*` a la API
(que recibe la ruta completa, p. ej. `/api/health`) y todo lo demás a la web. Las dos quedan
en el mismo dominio, así que comparten la protección de Vercel y no hace falta CORS.
