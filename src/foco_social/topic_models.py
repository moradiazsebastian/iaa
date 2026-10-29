"""Métodos de detección de tópicos intercambiables: KMeans, LDA y BERTopic.

Todos devuelven un `TopicFit` con la misma forma, así el grafo no depende del método:

- `labels`: tópico de cada mensaje (0..k-1). Los outliers de BERTopic ya vienen asignados
  al tópico más cercano.
- `confidence`: qué tan seguro es cada asignación (margen entre el mejor y el segundo
  tópico). Los outliers tienen 0, así que son los primeros que revisa el LLM.
- `sublabels`: subtópicos ya calculados para cada mensaje (solo BERTopic, que arma la
  jerarquía en un único ajuste). En el nivel siguiente se usan con `fit_presplit`.
"""

import logging
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

from foco_social.clustering import SPANISH_STOPWORDS, assignment_margin, cluster, embed
from foco_social.config import Settings

log = logging.getLogger(__name__)

MAX_AUTO_TOPICS = 8


@dataclass
class TopicFit:
    labels: np.ndarray
    confidence: np.ndarray
    sublabels: np.ndarray | None = None


def fit_topics(texts: list[str], n_topics: int | None, settings: Settings) -> TopicFit:
    """Agrupa `texts` con el método de `settings.topic_model`."""
    method = settings.topic_model
    if method == "lda":
        return _fit_lda(texts, n_topics, settings.seed)
    if method == "bertopic":
        return _fit_bertopic(texts, n_topics, settings.seed)
    return _fit_kmeans(texts, n_topics, settings)


def fit_presplit(
    texts: list[str], sublabels: list[int], n_topics: int | None, settings: Settings
) -> TopicFit | None:
    """Usa subtópicos calculados en el nivel anterior (jerarquía de BERTopic).

    Si hay más de `n_topics` (o más de MAX_AUTO_TOPICS en modo automático), se unen los
    más parecidos. Devuelve None si el grupo no tiene al menos dos subtópicos.
    """
    labels = _contiguous(np.asarray(sublabels))
    # Mensajes que el LLM movió desde otro tópico traen un subtópico ajeno a este grupo:
    # los subtópicos con menos de 3 mensajes se tratan como outliers.
    ids, counts = np.unique(labels, return_counts=True)
    small = np.isin(labels, ids[counts < 3])
    if len(ids[counts >= 3]) < 2:
        return None
    X = embed(texts, "sentence-transformers")
    labels, _ = _assign_outliers(X, np.where(small, -1, labels))

    n_fine = labels.max() + 1
    target = n_topics if n_topics is not None else (None if n_fine <= MAX_AUTO_TOPICS else 0)
    if target is not None and n_fine > max(target, 1):
        centroids = _centroids(X, labels)
        k = target or _best_merge(centroids)
        labels = _merge(centroids, k)[labels]
    return TopicFit(labels=labels, confidence=_confidence(X, labels, small))


# --- KMeans ---------------------------------------------------------------------


def _fit_kmeans(texts: list[str], n_topics: int | None, settings: Settings) -> TopicFit:
    X = embed(texts, settings.embeddings, settings.seed)
    labels, centroids = cluster(X, n_topics, settings.seed, max_k=MAX_AUTO_TOPICS)
    return TopicFit(labels=labels, confidence=assignment_margin(X, centroids))


# --- LDA ------------------------------------------------------------------------


def _fit_lda(texts: list[str], n_topics: int | None, seed: int) -> TopicFit:
    vectorizer = CountVectorizer(
        strip_accents="unicode",
        lowercase=True,
        stop_words=SPANISH_STOPWORDS,
        token_pattern=r"(?u)#?\b\w\w+\b",
    )
    counts = vectorizer.fit_transform(texts)

    def run(k: int) -> np.ndarray:
        lda = LatentDirichletAllocation(n_components=k, random_state=seed, max_iter=50)
        return lda.fit_transform(counts)  # distribución de tópicos de cada mensaje

    if n_topics is None:
        # Igual que con KMeans: el k cuyos grupos (tópico dominante) quedan mejor separados
        best = None
        for k in range(2, min(MAX_AUTO_TOPICS, len(texts) - 1) + 1):
            theta = run(k)
            labels = theta.argmax(axis=1)
            if len(set(labels.tolist())) < 2:
                continue
            score = silhouette_score(theta, labels)
            if best is None or score > best[0]:
                best = (score, theta)
        theta = best[1] if best else run(2)
    else:
        theta = run(n_topics)

    labels = _contiguous(theta.argmax(axis=1))  # algún tópico puede no ser dominante en nadie
    ordered = np.sort(theta, axis=1)
    return TopicFit(labels=labels, confidence=ordered[:, -1] - ordered[:, -2])


# --- BERTopic -------------------------------------------------------------------


def _fit_bertopic(texts: list[str], n_topics: int | None, seed: int) -> TopicFit:
    """BERTopic encuentra tópicos finos; se agrupan jerárquicamente en tópicos de nivel 1.

    Los tópicos finos quedan como subtópicos (`sublabels`). Es la misma idea que
    `BERTopic.hierarchical_topics`, que también une tópicos con clustering aglomerativo.
    """
    try:
        from bertopic import BERTopic
        from umap import UMAP
    except ImportError as e:
        raise ImportError('TOPIC_MODEL=bertopic requiere: pip install -e ".[bertopic]"') from e
    from sklearn.cluster import HDBSCAN

    X = embed(texts, "sentence-transformers")
    n = len(texts)
    model = BERTopic(
        umap_model=UMAP(
            n_neighbors=min(15, n - 1),
            n_components=5,
            min_dist=0.0,
            metric="cosine",
            random_state=seed,  # reproducible (desactiva el paralelismo de UMAP)
        ),
        hdbscan_model=HDBSCAN(min_cluster_size=max(5, n // 40)),
        vectorizer_model=CountVectorizer(stop_words=SPANISH_STOPWORDS, strip_accents="unicode"),
        calculate_probabilities=False,
    )
    raw, _ = model.fit_transform(texts, embeddings=X)
    raw = np.asarray(raw)
    log.info(
        "BERTopic: %d tópicos finos, %d outliers (%.0f%%)",
        len(set(raw.tolist()) - {-1}),
        int((raw == -1).sum()),
        100 * (raw == -1).mean(),
    )
    if len(set(raw.tolist()) - {-1}) < 2:
        # Sin estructura suficiente: se recurre a KMeans sobre los mismos embeddings
        labels, centroids = cluster(X, n_topics, seed, max_k=MAX_AUTO_TOPICS)
        return TopicFit(labels=labels, confidence=assignment_margin(X, centroids))

    fine, _ = _assign_outliers(X, _contiguous(raw))

    # Unir tópicos finos en tópicos de nivel 1
    centroids = _centroids(X, fine)
    n_fine = centroids.shape[0]
    if n_topics is not None and n_topics >= n_fine:
        return TopicFit(labels=fine, confidence=_confidence(X, fine, raw == -1))
    coarse = _merge(centroids, n_topics or _best_merge(centroids))[fine]
    return TopicFit(labels=coarse, confidence=_confidence(X, coarse, raw == -1), sublabels=fine)


def _merge(centroids: np.ndarray, k: int) -> np.ndarray:
    """Une tópicos en k grupos (clustering aglomerativo sobre sus centroides).

    Devuelve el grupo de cada tópico: `_merge(c, k)[labels]` da el grupo de cada mensaje.
    """
    model = AgglomerativeClustering(n_clusters=k, metric="cosine", linkage="average")
    return model.fit_predict(centroids)


def _best_merge(centroids: np.ndarray) -> int:
    """Cantidad de grupos de tópicos con mejor silhouette."""
    n = centroids.shape[0]
    if n <= 3:
        return n
    scored = [
        (silhouette_score(centroids, _merge(centroids, k), metric="cosine"), -k)
        for k in range(2, min(MAX_AUTO_TOPICS, n - 1) + 1)
    ]
    return -max(scored)[1]


# --- Auxiliares -----------------------------------------------------------------


def _contiguous(labels: np.ndarray) -> np.ndarray:
    """Renumera etiquetas como 0..k-1 (ignora -1)."""
    out = labels.copy()
    valid = labels != -1
    out[valid] = np.unique(labels[valid], return_inverse=True)[1]
    return out


def _centroids(X: np.ndarray, labels: np.ndarray) -> np.ndarray:
    k = labels.max() + 1
    return normalize(np.vstack([X[labels == c].mean(axis=0) for c in range(k)]))


def _confidence(X: np.ndarray, labels: np.ndarray, outliers: np.ndarray) -> np.ndarray:
    confidence = assignment_margin(X, _centroids(X, labels))
    confidence[outliers] = 0.0
    return confidence


def _assign_outliers(X: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Asigna los -1 al centroide más cercano; su confianza queda en 0."""
    outliers = labels == -1
    labels = _contiguous(labels)
    centroids = _centroids(X, np.where(outliers, -1, labels)) if outliers.any() else None
    if centroids is not None:
        labels[outliers] = (X[outliers] @ centroids.T).argmax(axis=1)
    return labels, _confidence(X, labels, outliers)
