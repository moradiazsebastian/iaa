"""Configuración global, leída de variables de entorno / .env."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: Literal["anthropic", "openai", "ollama", "none"] = "anthropic"
    llm_model: str = "claude-opus-5-5"
    llm_effort: Literal["low", "medium", "high"] | None = "low"
    llm_cache: bool = True
    llm_base_url: str | None = None  # p. ej. un servidor Ollama en otra máquina
    llm_num_ctx: int = 16384  # ventana de contexto para Ollama (su default es chico)

    data_path: Path = Path("data/sample/tweets.csv")
    topic_model: Literal["kmeans", "lda", "bertopic"] = "kmeans"
    embeddings: Literal["tfidf", "sentence-transformers"] = "tfidf"  # solo para kmeans
    max_llm_reassign: int = 120  # tope de mensajes dudosos que revisa el LLM por nivel
    seed: int = 42

    runs_dir: Path = Path("runs")
    cache_dir: Path = Path(".cache")


def get_settings(**overrides) -> Settings:
    return Settings(**{k: v for k, v in overrides.items() if v is not None})
