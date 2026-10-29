from datetime import datetime
from typing import TypedDict

from foco_social.schemas import Topic, Tweet


class PendingSplit(TypedDict):
    path: str  # "" para la raíz, "2" para el tópico 2, "2.1" para un subtópico...
    name: str | None
    tweet_ids: list[str]
    level: int  # nivel de los tópicos que se van a generar (1 = tópicos, 2 = subtópicos)


class AgentState(TypedDict, total=False):
    # Entrada (definida por el usuario)
    theme: str
    keywords: list[str]
    n_topics: int | None  # None = elegir automáticamente
    n_subtopics: int | None
    depth: int  # 1 = solo tópicos, 2 = tópicos + subtópicos, ...
    max_tweets: int
    since: datetime | None
    until: datetime | None

    # Construido por el agente
    tweets: dict[str, Tweet]
    queue: list[PendingSplit]
    topics: list[Topic]
    assignments: dict[str, str]  # tweet_id -> path del tópico más específico
    presplit: dict[str, int]  # tweet_id -> subtópico ya calculado (jerarquía de BERTopic)
