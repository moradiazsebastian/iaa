"""Dataset estático (CSV o Parquet) consultado con DuckDB."""

import unicodedata
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from foco_social.schemas import Tweet

TWEET_COLUMNS = ["id", "created_at", "author", "author_followers", "text", "likes", "retweets"]


def normalize(text: str) -> str:
    """Minúsculas y sin acentos, igual que strip_accents(lower(...)) en DuckDB."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


class StaticSource:
    def __init__(self, path: str | Path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el dataset: {path}")
        reader = "read_parquet" if path.suffix == ".parquet" else "read_csv_auto"
        self.con = duckdb.connect()
        literal = str(path).replace("'", "''")
        self.con.execute(f"CREATE VIEW tweets AS SELECT * FROM {reader}('{literal}')")

    def search(
        self,
        keywords: list[str],
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 1000,
    ) -> list[Tweet]:
        keywords = [normalize(k).strip() for k in keywords if k.strip()]
        if not keywords:
            return []
        where = ["(" + " OR ".join(["strip_accents(lower(text)) LIKE ?"] * len(keywords)) + ")"]
        params: list = [f"%{k}%" for k in keywords]
        if since:
            where.append("created_at >= ?")
            params.append(since)
        if until:
            where.append("created_at <= ?")
            params.append(until)
        params.append(limit)
        # Orden determinístico: primero los mensajes con más interacción
        query = f"""
            SELECT {", ".join(TWEET_COLUMNS)} FROM tweets
            WHERE {" AND ".join(where)}
            ORDER BY likes + retweets DESC, id
            LIMIT ?
        """
        df = self.con.execute(query, params).df()
        return [Tweet(**{**row, "id": str(row["id"])}) for row in df.to_dict("records")]

    def sql(self, query: str) -> pd.DataFrame:
        """Consulta SQL de solo lectura sobre la vista `tweets`."""
        if not query.lstrip().lower().startswith(("select", "with")):
            raise ValueError("Solo se permiten consultas SELECT")
        return self.con.execute(query).df()

    def labels(self) -> pd.DataFrame | None:
        """Etiquetas manuales (topic, subtopic) si el dataset las tiene; se usan para evaluar."""
        cols = set(self.con.execute("SELECT * FROM tweets LIMIT 0").df().columns)
        if "topic" not in cols:
            return None
        sub = "subtopic" if "subtopic" in cols else "NULL AS subtopic"
        df = self.con.execute(f"SELECT CAST(id AS VARCHAR) AS id, topic, {sub} FROM tweets").df()
        return df.set_index("id")
