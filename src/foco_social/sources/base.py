from datetime import datetime
from typing import Protocol

from foco_social.schemas import Tweet


class TweetSource(Protocol):
    """Interfaz común para cualquier origen de mensajes (dataset estático, replay, API de X)."""

    def search(
        self,
        keywords: list[str],
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 1000,
    ) -> list[Tweet]:
        """Devuelve mensajes que contienen al menos una de las keywords."""
        ...
