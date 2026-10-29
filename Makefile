THEME ?= elecciones presidenciales
ARGS ?=

.PHONY: setup run run-offline eval repro test lint sample

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

test:
	pytest -q

lint:
	ruff check src tests
	ruff format --check src tests

sample:           ## Regenera data/sample/tweets.csv
	foco make-sample
