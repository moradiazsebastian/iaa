# `cli.py`: línea de comandos

Punto de entrada del comando `foco`, declarado en `pyproject.toml` (`[project.scripts]`).
Usa `argparse` y delega el trabajo real a `runner.py`.

## Comandos

| Comando | Función | Qué hace |
|---|---|---|
| `foco run` | `cmd_run` | Ejecuta el análisis, guarda los resultados e imprime `report.md` |
| `foco eval` | `cmd_eval` | Igual que `run`, y además compara contra las columnas `topic` / `subtopic` del dataset. Guarda `eval.json` |
| `foco repro` | `cmd_repro` | Ejecuta dos veces **con la caché del LLM desactivada** y compara las dos corridas entre sí. Guarda `repro.json`, `run1/` y `run2/` |
| `foco compare` | `cmd_compare` | Corre cada método de tópicos con y sin LLM y arma una tabla de métricas (ver abajo) |
| `foco make-sample` | `cmd_make_sample` | Regenera `data/sample/tweets.csv` con `evaluation/synthetic.py` |

Todos los comandos de análisis comparten las opciones `--theme`, `--keywords`, `--topics`,
`--subtopics`, `--depth`, `--max-tweets`, `--since`, `--until`, `--data`, `--provider` y
`--model`. Se definen una sola vez en el parser `analysis` y se heredan con `parents=[...]`.
`run`, `eval` y `repro` además aceptan `--method` (parser `single`), que pisa `TOPIC_MODEL`.

## `foco compare`

```bash
foco compare --theme "elecciones" --methods kmeans,lda,bertopic --llm both --topics 4
```

- `--methods`: métodos separados por coma (por defecto, los tres).
- `--llm both|on|off`: con LLM, sin LLM o ambos (por defecto, ambos).

Para que la comparación sea justa, las keywords se calculan **una sola vez** (las de
`--keywords` o, si no hay, las que proponga el LLM) y todas las celdas buscan los mismos
mensajes. Cada celda guarda su corrida en `runs/<id>/<método>-llm/` o `<método>-sin-llm/`,
con su `eval.json`. La tabla final queda en `results.csv` y `results.md`: mensajes, tópicos,
ARI / NMI / accuracy de tópicos y subtópicos, segundos y llamadas al LLM.

Si BERTopic no está instalado, esa celda se omite con una advertencia y el resto sigue.

## Funciones auxiliares

- **`main()`**: carga `.env` al entorno con `load_dotenv()`, para que LangChain encuentre
  las API keys. En Windows fuerza la consola a UTF-8 para que se vean los acentos.
- **`_settings(args, **overrides)`**: arma la configuración. Las opciones de la línea de
  comandos (`--data`, `--provider`, `--model`) pisan lo que diga `.env`.
- **`_analyze(args, settings, keywords=None)`**: convierte los argumentos en una llamada a
  `run_analysis()`. `keywords` permite pasar keywords ya calculadas (lo usa `compare`).
- **`_evaluate(result, gold, depth)`**: calcula las métricas contra las etiquetas manuales
  (lo usan `eval` y `compare`).
- **`_markdown_table(df)`**: tabla Markdown para `results.md`.
- **`_start_run(settings, theme, kind)`**: crea la carpeta `runs/<fecha>-<tipo>-<tema>/`
  y configura el logging: mensajes INFO del proyecto en consola y en `run.log`. Las
  librerías externas solo muestran advertencias.

## Cómo se evalúa (`_evaluate`)

1. Lee las etiquetas manuales con `StaticSource.labels()`.
2. Recorta las asignaciones predichas al nivel 1 (`"2.1"` → `"2"`) y las compara con `topic`.
3. Si hay subtópicos y `--depth >= 2`, compara el nivel 2 con `topic / subtopic`.
4. Reemplaza los paths del emparejamiento por `path + nombre` para que se lea mejor.

## Para agregar un comando

Crear `cmd_<nombre>(args)`, registrarlo en `_build_parser()` con `sub.add_parser(...)` y
`p.set_defaults(func=cmd_<nombre>)`.
