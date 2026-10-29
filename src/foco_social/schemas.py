"""Modelos de datos del dominio y esquemas de salida estructurada del LLM."""

from datetime import datetime

from pydantic import BaseModel, Field


class Tweet(BaseModel):
    id: str
    created_at: datetime
    author: str
    author_followers: int = 0
    text: str
    likes: int = 0
    retweets: int = 0


# --- Salidas estructuradas del LLM --------------------------------------------


class SearchPlan(BaseModel):
    """Plan de búsqueda generado a partir de la temática del usuario."""

    keywords: list[str] = Field(
        description="Palabras clave y hashtags (minúsculas, sin acentos) para buscar mensajes "
        "sobre la temática. Incluir sinónimos, siglas y nombres propios relevantes."
    )


class TopicLabel(BaseModel):
    cluster_id: int = Field(description="Identificador del cluster que se está describiendo")
    name: str = Field(description="Nombre corto del tópico (2 a 5 palabras)")
    description: str = Field(description="Una oración que describe de qué hablan los mensajes")


class TopicLabels(BaseModel):
    topics: list[TopicLabel]


class Assignment(BaseModel):
    tweet_index: int = Field(description="Índice del mensaje en la lista recibida")
    cluster_id: int = Field(description="cluster_id del tópico que mejor describe el mensaje")


class Assignments(BaseModel):
    assignments: list[Assignment]


# --- Resultado del análisis ---------------------------------------------------


class Topic(BaseModel):
    path: str = Field(description="Ruta jerárquica, p. ej. '2' o '2.1'")
    name: str
    description: str
    level: int
    n_tweets: int
    share_of_parent: float
    share_of_total: float
    sample_tweet_ids: list[str] = []
