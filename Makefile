THEME ?= elecciones presidenciales
ARGS ?=

.PHONY: setup run run-offline eval repro api test lint sample

setup:            ## Crea .venv e instala el proyecto
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	cp -n .env.example .env || true

run:              ## Análisis con LLM:  make run THEME="elecciones" ARGS="--topics 5"
	foco run --theme "$(THEME)" $(ARGS)

run-offline:      ## Análisis sin LLM (no requiere API key)
	foco run --theme "$(THEME)" --keywords debate,encuesta,fraude,voto,inflacion,candidato --provider none $(ARGS)

eval:             ## Compara contra las etiquetas manuales del dataset
	foco eval --theme "$(THEME)" $(ARGS)

repro:            ## Corre dos veces sin caché y mide cuánto difieren
	foco repro --theme "$(THEME)" $(ARGS)

api:              ## API para la app web en http://localhost:8000 (docs en /docs)
	uvicorn foco_social.api:app --reload --port 8000

test:
	pytest -q

lint:
	ruff check src tests api
	ruff format --check src tests api

sample:           ## Regenera data/sample/tweets.csv
	foco make-sample
