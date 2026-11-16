"""API HTTP del agente (FastAPI). La usa la app web; la CLI no la necesita.

Local:   uvicorn foco_social.api:app --reload --port 8000
Vercel:  se despliega a través de api/index.py
"""

import logging
import os
import tempfile
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from foco_social import __version__
from foco_social.config import Settings, get_settings
from foco_social.evaluation.metrics import evaluate
from foco_social.runner import run_analysis
from foco_social.schemas import Topic
from foco_social.sources import StaticSource

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]  # raíz del repositorio

app = FastAPI(title="Foco Social API", version=__version__)
app.add_middleware(
    CORSMiddleware,
    # Solo para desarrollo local: en Vercel la web y la API comparten dominio
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --- Contrato -------------------------------------------------------------------


class RunRequest(BaseModel):
    theme: str = Field(min_length=2, max_length=200, examples=["elecciones presidenciales"])
    keywords: list[str] | None = Field(
        None, description="Si se omite, las propone el LLM a partir de la temática"
    )
    method: Literal["kmeans", "lda", "bertopic"] = "kmeans"
    n_topics: int | None = Field(None, ge=2, le=15, description="None = automático")
    n_subtopics: int | None = Field(None, ge=2, le=10, description="None = automático")
    depth: int = Field(2, ge=1, le=3, description="1 = tópicos, 2 = + subtópicos")
    max_tweets: int = Field(2000, ge=10, le=5000)
    since: datetime | None = None
    until: datetime | None = None
    use_llm: bool = True
    evaluate: bool = Field(True, description="Comparar contra etiquetas manuales, si hay")


class TweetAssignment(BaseModel):
    id: str
    topic_path: str
    topic: str
    subtopic: str
    text: str


class RunResponse(BaseModel):
    theme: str
    method: str
    llm: str | None = Field(description="Modelo usado, o None si se corrió sin LLM")
    keywords: list[str]
    stats: dict = Field(description="seconds, n_tweets, llm_calls, llm_cache_hits")
    topics: list[Topic]
    assignments: list[TweetAssignment]
    metrics: dict | None = Field(description="ARI / NMI / matched_accuracy, si hay etiquetas")


class Options(BaseModel):
    methods: list[str]
    llm_available: bool
    llm_provider: str
    llm_model: str
    dataset: str
    dataset_has_labels: bool


# --- Endpoints ------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/options", response_model=Options)
def options() -> Options:
    """Qué puede elegir la interfaz: métodos instalados y si hay un LLM configurado."""
    settings = _settings()
    methods = ["kmeans", "lda"] + (["bertopic"] if find_spec("bertopic") else [])
    return Options(
        methods=methods,
        llm_available=_llm_available(settings),
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        dataset=settings.data_path.name,
        dataset_has_labels=StaticSource(settings.data_path).labels() is not None,
    )


@app.post("/api/runs", response_model=RunResponse)
def create_run(req: RunRequest) -> RunResponse:
    """Ejecuta el agente y devuelve tópicos, asignaciones y métricas."""
    settings = _settings(method=req.method, use_llm=req.use_llm)
    if req.use_llm and not _llm_available(settings):
        raise HTTPException(503, "No hay un LLM configurado. Reintentá con use_llm=false.")

    try:
        result = run_analysis(
            settings,
            theme=req.theme,
            keywords=req.keywords,
            n_topics=req.n_topics,
            n_subtopics=req.n_subtopics,
            depth=req.depth,
            max_tweets=req.max_tweets,
            since=req.since,
            until=req.until,
        )
    except ValueError as e:  # no se encontraron mensajes
        raise HTTPException(404, str(e)) from e
    except ImportError as e:  # método no instalado (p. ej. BERTopic)
        raise HTTPException(400, str(e)) from e

    frame = result.assignments_frame()
    metrics = None
    gold = StaticSource(settings.data_path).labels() if req.evaluate else None
    if gold is not None:
        metrics = evaluate(
            frame.set_index("id")["topic_path"], gold, req.depth, result.topic_names()
        )

    return RunResponse(
        theme=req.theme,
        method=req.method,
        llm=settings.llm_model if settings.llm_provider != "none" else None,
        keywords=result.keywords,
        stats=result.stats,
        topics=result.topics,
        assignments=frame.to_dict("records"),
        metrics=metrics,
    )


# --- Auxiliares -----------------------------------------------------------------


def _settings(method: str | None = None, use_llm: bool = True) -> Settings:
    settings = get_settings(topic_model=method)
    updates: dict = {}
    if not settings.data_path.is_absolute():
        updates["data_path"] = ROOT / settings.data_path
    if os.environ.get("VERCEL"):
        # En Vercel solo /tmp es escribible
        updates["cache_dir"] = Path(tempfile.gettempdir()) / "foco-cache"
    if not use_llm:
        updates["llm_provider"] = "none"
    return settings.model_copy(update=updates)


def _llm_available(settings: Settings) -> bool:
    keys = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
    if settings.llm_provider == "none":
        return False
    key = keys.get(settings.llm_provider)
    return key is None or bool(os.environ.get(key))
