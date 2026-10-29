"""Ejecuta el agente de punta a punta y guarda los resultados en runs/<id>/."""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from foco_social.config import Settings
from foco_social.graph import build_graph
from foco_social.llm import LLM
from foco_social.schemas import Topic
from foco_social.sources import StaticSource, TweetSource

log = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    params: dict
    keywords: list[str]
    topics: list[Topic]
    assignments: dict[str, str]  # tweet_id -> path del tópico más específico
    texts: dict[str, str]
    stats: dict = field(default_factory=dict)

    def topic_names(self) -> dict[str, str]:
        return {t.path: t.name for t in self.topics}

    def assignments_frame(self) -> pd.DataFrame:
        names = self.topic_names()
        rows = []
        for tweet_id, path in self.assignments.items():
            level1 = path.split(".")[0] if path else ""
            rows.append(
                {
                    "id": tweet_id,
                    "topic_path": path,
                    "topic": names.get(level1, "(sin tópico)"),
                    "subtopic": names.get(path, "") if "." in path else "",
                    "text": self.texts[tweet_id],
                }
            )
        return pd.DataFrame(rows)


def run_analysis(
    settings: Settings,
    theme: str,
    keywords: list[str] | None = None,
    n_topics: int | None = None,
    n_subtopics: int | None = None,
    depth: int = 2,
    max_tweets: int = 2000,
    since: datetime | None = None,
    until: datetime | None = None,
    source: TweetSource | None = None,
    llm: LLM | None = None,
) -> AnalysisResult:
    source = source or StaticSource(settings.data_path)
    llm = llm or LLM(settings)
    graph = build_graph(source, llm, settings)

    params = {
        "theme": theme,
        "keywords": keywords or [],
        "n_topics": n_topics,
        "n_subtopics": n_subtopics,
        "depth": depth,
        "max_tweets": max_tweets,
        "since": since,
        "until": until,
    }
    started = time.perf_counter()
    state = graph.invoke(params, config={"recursion_limit": 500})
    elapsed = time.perf_counter() - started

    return AnalysisResult(
        params={**params, "since": str(since or ""), "until": str(until or "")},
        keywords=state["keywords"],
        topics=sorted(state["topics"], key=lambda t: [int(p) for p in t.path.split(".")]),
        assignments=state["assignments"],
        texts={i: t.text for i, t in state["tweets"].items()},
        stats={
            "seconds": round(elapsed, 1),
            "n_tweets": len(state["tweets"]),
            "llm_calls": llm.calls,
            "llm_cache_hits": llm.cache_hits,
        },
    )


def save_run(result: AnalysisResult, settings: Settings, run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "params": result.params,
        "keywords": result.keywords,
        "stats": result.stats,
        "settings": settings.model_dump(mode="json"),
    }
    (run_dir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), "utf-8")
    (run_dir / "topics.json").write_text(
        json.dumps([t.model_dump() for t in result.topics], indent=2, ensure_ascii=False), "utf-8"
    )
    result.assignments_frame().to_csv(run_dir / "assignments.csv", index=False, encoding="utf-8")
    (run_dir / "report.md").write_text(render_report(result), "utf-8")
    return run_dir


def render_report(result: AnalysisResult) -> str:
    lines = [
        f"# Tópicos: {result.params['theme']}",
        "",
        f"- Mensajes analizados: {result.stats['n_tweets']}",
        f"- Keywords: {', '.join(result.keywords)}",
        (
            f"- Tiempo: {result.stats['seconds']} s · llamadas al LLM: {result.stats['llm_calls']}"
            f" (caché: {result.stats['llm_cache_hits']})"
        ),
        "",
    ]
    for t in result.topics:
        indent = "  " * (t.level - 1)
        lines.append(
            f"{indent}- **{t.path} {t.name}** — {t.n_tweets} mensajes "
            f"({t.share_of_total:.0%} del total, {t.share_of_parent:.0%} del nivel superior)"
        )
        lines.append(f"{indent}  {t.description}")
        for tweet_id in t.sample_tweet_ids:
            text = " ".join(result.texts[tweet_id].split())
            lines.append(f"{indent}  > {text}")
    return "\n".join(lines) + "\n"
