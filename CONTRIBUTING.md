# Cómo contribuir

`main` es la versión desplegada en Vercel: la app web, la API y la CLI. Nadie hace push
directo a `main`. Todo cambio entra por una rama y un pull request.

## Flujo

```bash
git checkout main
git pull
git checkout -b feature/<nombre-corto>     # p. ej. feature/prompt-keywords

# ... cambios, tests ...
pytest -q
ruff check src tests api && ruff format src tests api

git push -u origin feature/<nombre-corto>
```

Después, abrir un pull request hacia `main` en GitHub (o `gh pr create`).

En cada pull request corren automáticamente:

- **CI de GitHub Actions**: lint, tests y una evaluación completa de la CLI sin LLM.
- **Preview de Vercel**: la app desplegada con los cambios de la rama, en su propia URL.

Se mergea cuando la CI pasa y alguien del equipo revisó el cambio.

## Nombres de ramas

| Prefijo | Para |
|---|---|
| `feature/` | funcionalidad nueva (CLI, agente, API o web) |
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
