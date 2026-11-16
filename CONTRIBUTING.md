# Cómo contribuir

Hay dos ramas base. Nadie hace push directo a ninguna de las dos: todo cambio entra por una
rama propia y un pull request.

| Rama base | Contenido | Para trabajar en |
|---|---|---|
| `feature/cli` | la CLI y el agente, sin la app web ni la configuración de Vercel | el agente, los prompts, los métodos de tópicos, la evaluación, la CLI |
| `main` | la versión desplegada en Vercel: CLI + API + app web | la API (`src/foco_social/api.py`), la web (`web/`), la configuración de Vercel |

```
feature/cli ──●──●──●───────●──→   trabajo en la CLI y el agente
                     \        \
main        ──●───────●────────●─→  app desplegada (recibe feature/cli por pull request)
```

## Flujo para la CLI y el agente

```bash
git checkout feature/cli
git pull
git checkout -b feature/<nombre-corto>     # p. ej. feature/prompt-keywords

# ... cambios, tests ...
pytest -q
ruff check src tests && ruff format src tests

git push -u origin feature/<nombre-corto>
```

Después, abrir un pull request **hacia `feature/cli`** (en GitHub, o
`gh pr create --base feature/cli`).

Cuando `feature/cli` tiene cambios listos para la app, se abre un pull request de
`feature/cli` hacia `main`. Así la app desplegada recibe las mejoras del agente sin que
`feature/cli` reciba los archivos de la web.

## Flujo para la API y la web

Igual, pero partiendo de `main` y con el pull request hacia `main`:

```bash
git checkout main
git pull
git checkout -b feature/<nombre-corto>
# ...
ruff check src tests api && ruff format src tests api
```

## Reglas para que las dos ramas no se separen

- **Los cambios al agente (`src/foco_social/`, salvo `api.py`) van por `feature/cli`**, aunque
  los necesite la web. Si se hacen directo en `main`, `feature/cli` no los recibe.
- **No mergear `main` en `feature/cli`**: traería la API y la configuración de Vercel. Si hace
  falta un arreglo que ya está en `main`, copiarlo con `git cherry-pick <commit>`.
- **Mergear `feature/cli` en `main` seguido** (por ejemplo, cada vez que se cierra una mejora),
  para que las diferencias sean chicas y no haya conflictos grandes.

## Qué corre en cada pull request

- **CI de GitHub Actions**: lint, tests y una evaluación completa de la CLI sin LLM.
- **Preview de Vercel**: solo en ramas que parten de `main`. Las ramas de `feature/cli` no
  tienen la app web, así que Vercel no las construye.

Se mergea cuando la CI pasa y alguien del equipo revisó el cambio.

## Nombres de ramas

| Prefijo | Para |
|---|---|
| `feature/` | funcionalidad nueva (CLI, agente, API o web). Excepción: `feature/cli` es una rama base permanente |
| `fix/` | corrección de un error |
| `docs/` | solo documentación |
| `exp/` | experimentos que quizás no se mergeen |

## Qué toca cada parte

| Carpeta | Contenido | Requiere |
|---|---|---|
| `src/foco_social/` | agente, CLI y API | Python |
| `web/` | interfaz web (Next.js) | Node.js |
| `tests/` | tests de Python | Python |
| `docs/` | documentación por archivo | |

Un cambio en el agente (`src/`) afecta a la CLI y a la app web a la vez: por eso los tests y
la preview de Vercel corren en cada pull request.

## Antes de abrir el pull request

- [ ] `pytest -q` pasa
- [ ] `ruff check` y `ruff format` sin cambios pendientes
- [ ] Si cambiaste un archivo de `src/`, actualizaste su doc en `docs/`
- [ ] Si agregaste una carpeta o archivo en la raíz, lo sumaste a `.gitignore` (es una lista blanca)
- [ ] Sin API keys ni datos reales en el commit (`.env` y `data/` reales no se suben)
