"""Simula una red social en tiempo real reproduciendo un dataset estático por timestamp.

El agente solo ve los mensajes publicados hasta el "ahora" simulado; avanzar el reloj
hace aparecer mensajes nuevos. Sirve como test environment de tiempo real sin
depender de la API de X.
"""

from datetime import datetime, timedelta

from foco_social.schemas import Tweet
from foco_social.sources.static import StaticSource


class ReplaySource(StaticSource):
    def __init__(self, path, start: datetime | None = None):
        super().__init__(path)
        first = self.con.execute("SELECT min(created_at) FROM tweets").fetchone()[0]
        self.now: datetime = start or first

    def advance(self, delta: timedelta) -> None:
        self.now += delta

    def search(
        self,
        keywords: list[str],
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 1000,
    ) -> list[Tweet]:
        until = min(until, self.now) if until else self.now
        return super().search(keywords, since=since, until=until, limit=limit)
