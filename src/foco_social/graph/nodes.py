"""Nodos del grafo. Cada nodo recibe el estado y devuelve solo las claves que modifica."""

import logging
import zlib

import numpy as np

from foco_social import prompts
from foco_social.clustering import top_terms
from foco_social.config import Settings
from foco_social.graph.state import AgentState, PendingSplit
from foco_social.llm import LLM
from foco_social.schemas import Assignments, SearchPlan, Topic, TopicLabels, Tweet
from foco_social.sources import TweetSource
from foco_social.topic_models import fit_presplit, fit_topics

log = logging.getLogger(__name__)


def plan_keywords(theme: str, llm: LLM) -> list[str]:
    """La temática (partida por comas) más las keywords que proponga el LLM."""
    keywords = [k.strip().lower() for k in theme.split(",") if k.strip()]
    if llm.enabled:
        keywords += llm.structured(
            SearchPlan, prompts.PLAN_SYSTEM, prompts.plan_user(theme)
        ).keywords
    return list(dict.fromkeys(keywords))


class Nodes:
    def __init__(
        self,
        source: TweetSource,
        llm: LLM,
        settings: Settings,
        min_tweets_to_split: int = 12,
        samples_per_cluster: int = 8,
        ambiguous_quantile: float = 0.15,
        assign_batch_size: int = 40,
    ):
        self.source = source
        self.llm = llm
        self.settings = settings
        self.min_tweets_to_split = min_tweets_to_split
        self.samples_per_cluster = samples_per_cluster
        self.ambiguous_quantile = ambiguous_quantile
        self.assign_batch_size = assign_batch_size

    # --- Nodos ----------------------------------------------------------------

    def plan_queries(self, state: AgentState) -> dict:
        """Expande la temática en keywords de búsqueda (salvo que el usuario las haya dado)."""
        if state.get("keywords"):
            return {}
        keywords = plan_keywords(state["theme"], self.llm)
        log.info("Keywords: %s", keywords)
        return {"keywords": keywords}

    def retrieve(self, state: AgentState) -> dict:
        tweets = self.source.search(
            state["keywords"],
            since=state.get("since"),
            until=state.get("until"),
            limit=state.get("max_tweets", 2000),
        )
        log.info("Recuperados %d mensajes", len(tweets))
        if not tweets:
            raise ValueError(f"No se encontraron mensajes para las keywords {state['keywords']}")
        ids = [t.id for t in tweets]
        return {
            "tweets": {t.id: t for t in tweets},
            "queue": [PendingSplit(path="", name=None, tweet_ids=ids, level=1)],
            "topics": [],
            "assignments": {i: "" for i in ids},
            "presplit": {},
        }

    def split_topic(self, state: AgentState) -> dict:
        """Divide el primer elemento de la cola en (sub)tópicos y los agrega al resultado."""
        item, rest = state["queue"][0], state["queue"][1:]
        ids = item["tweet_ids"]
        if len(ids) < self.min_tweets_to_split:
            return {"queue": rest}

        tweets = [state["tweets"][i] for i in ids]
        texts = [t.text for t in tweets]
        k = state.get("n_topics") if item["level"] == 1 else state.get("n_subtopics")

        presplit = state.get("presplit", {})
        if item["level"] > 1 and all(i in presplit for i in ids):
            fit = fit_presplit(texts, [presplit[i] for i in ids], k, self.settings)
        else:
            fit = fit_topics(texts, k, self.settings)
        if fit is None or len(set(fit.labels.tolist())) < 2:
            return {"queue": rest}
        if fit.sublabels is not None:
            presplit = {**presplit, **dict(zip(ids, fit.sublabels.tolist()))}

        names = self._label(state["theme"], item, tweets, fit.labels)
        labels = self._reassign_ambiguous(fit.confidence, fit.labels, texts, names)

        # Numerar los clusters por tamaño (el más grande es .1)
        cluster_ids, sizes = np.unique(labels, return_counts=True)
        order = cluster_ids[np.argsort(-sizes, kind="stable")]
        prefix = f"{item['path']}." if item["path"] else ""
        assignments = dict(state["assignments"])
        new_topics, children = [], []
        for rank, cid in enumerate(order, start=1):
            path = f"{prefix}{rank}"
            members = [ids[j] for j in np.flatnonzero(labels == cid)]
            name, description = names[int(cid)]
            new_topics.append(
                Topic(
                    path=path,
                    name=name,
                    description=description,
                    level=item["level"],
                    n_tweets=len(members),
                    share_of_parent=len(members) / len(ids),
                    share_of_total=len(members) / len(state["tweets"]),
                    sample_tweet_ids=self._top_by_engagement(
                        [state["tweets"][m] for m in members], 3
                    ),
                )
            )
            assignments.update({m: path for m in members})
            if item["level"] < state.get("depth", 1):
                children.append(
                    PendingSplit(path=path, name=name, tweet_ids=members, level=item["level"] + 1)
                )

        log.info(
            "Nivel %d%s: %d tópicos",
            item["level"],
            f" (dentro de {item['path']} {item['name']})" if item["path"] else "",
            len(new_topics),
        )
        return {
            "queue": rest + children,
            "topics": state["topics"] + new_topics,
            "assignments": assignments,
            "presplit": presplit,
        }

    # --- Auxiliares -----------------------------------------------------------

    def _label(
        self, theme: str, item: PendingSplit, tweets: list[Tweet], labels: np.ndarray
    ) -> dict[int, tuple[str, str]]:
        """Nombre y descripción de cada cluster: con el LLM, o con términos TF-IDF si no hay LLM."""
        terms = top_terms([t.text for t in tweets], labels)
        fallback = {c: (", ".join(ts[:3]), "Términos: " + ", ".join(ts)) for c, ts in terms.items()}
        if not self.llm.enabled:
            return fallback

        rng = np.random.default_rng(self.settings.seed + zlib.crc32(item["path"].encode()))
        clusters = []
        for c in sorted(terms):
            members = [t for t, lab in zip(tweets, labels) if lab == c]
            clusters.append(
                {
                    "cluster_id": c,
                    "size": len(members),
                    "terms": terms[c],
                    "samples": [self._format(t) for t in self._sample(members, rng)],
                }
            )
        result = self.llm.structured(
            TopicLabels, prompts.LABEL_SYSTEM, prompts.label_user(theme, item["name"], clusters)
        )
        names = dict(fallback)
        names.update(
            {t.cluster_id: (t.name, t.description) for t in result.topics if t.cluster_id in names}
        )
        return names

    def _reassign_ambiguous(
        self,
        confidence: np.ndarray,
        labels: np.ndarray,
        texts: list[str],
        names: dict[int, tuple[str, str]],
    ) -> np.ndarray:
        """Le pide al LLM que reclasifique los mensajes con menor confianza.

        Entran el `ambiguous_quantile` menos seguro y siempre los outliers (confianza 0),
        hasta `MAX_LLM_REASSIGN` mensajes por nivel.
        """
        if not self.llm.enabled:
            return labels
        threshold = max(np.quantile(confidence, self.ambiguous_quantile), 0.0)
        order = np.argsort(confidence, kind="stable")
        ambiguous = [i for i in order if confidence[i] <= threshold]
        ambiguous = ambiguous[: self.settings.max_llm_reassign]
        if not ambiguous:
            return labels

        topics = [{"cluster_id": c, "name": n, "description": d} for c, (n, d) in names.items()]
        labels = labels.copy()
        changed = 0
        for start in range(0, len(ambiguous), self.assign_batch_size):
            batch = ambiguous[start : start + self.assign_batch_size]
            result = self.llm.structured(
                Assignments,
                prompts.ASSIGN_SYSTEM,
                prompts.assign_user(topics, [texts[i] for i in batch]),
            )
            for a in result.assignments:
                if 0 <= a.tweet_index < len(batch) and a.cluster_id in names:
                    i = batch[a.tweet_index]
                    changed += int(labels[i] != a.cluster_id)
                    labels[i] = a.cluster_id
        log.info("Reasignación LLM: %d ambiguos revisados, %d cambiados", len(ambiguous), changed)
        return labels

    def _sample(self, members: list[Tweet], rng: np.random.Generator) -> list[Tweet]:
        """Mitad los de más interacción, mitad al azar (con semilla) para no sesgar hacia lo viral."""
        n_top = self.samples_per_cluster // 2
        by_engagement = sorted(members, key=lambda t: (-(t.likes + t.retweets), t.id))
        top, others = by_engagement[:n_top], by_engagement[n_top:]
        n_random = min(self.samples_per_cluster - n_top, len(others))
        picked = rng.choice(len(others), size=n_random, replace=False) if n_random else []
        return top + [others[i] for i in sorted(picked)]

    @staticmethod
    def _format(t: Tweet) -> str:
        text = " ".join(t.text.split())
        return f"[{t.likes} likes, autor con {t.author_followers} seguidores] {text}"

    @staticmethod
    def _top_by_engagement(tweets: list[Tweet], n: int) -> list[str]:
        return [t.id for t in sorted(tweets, key=lambda t: (-(t.likes + t.retweets), t.id))[:n]]
