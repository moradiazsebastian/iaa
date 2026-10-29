"""Vectorización + clustering: la parte "clásica" del pipeline.

El LLM no ve todos los mensajes: el clustering propone grupos y el LLM los nombra,
y solo revisa los mensajes ambiguos (ver graph/nodes.py).
"""

from functools import lru_cache

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

SPANISH_STOPWORDS = """
a al algo algun alguna algunas alguno algunos ante antes asi aun aunque bien cada como con
contra cual cuando de del desde donde dos el ella ellas ello ellos en entre era es esa esas
ese eso esos esta estaba estado estan estar este esto estos fue fueron ha hace hacer han hasta
hay la las le les lo los mas me mi mientras muy nada ni no nos nosotros o otra otras otro otros
para pero poco por porque que quien se sea ser si sin sobre solo son su sus tambien tan tanto
te tiene tienen todo todos tu un una uno unos usted va vamos y ya yo rt via https http co amp
""".split()


def embed(texts: list[str], method: str = "tfidf", seed: int = 42) -> np.ndarray:
    """Devuelve una matriz (n_textos, dim) con filas de norma 1."""
    if method == "sentence-transformers":
        # Caché por texto: los subtópicos reutilizan los embeddings del nivel anterior
        missing = [t for t in dict.fromkeys(texts) if t not in _embedding_cache]
        if missing:
            vectors = _sentence_model().encode(
                missing, normalize_embeddings=True, show_progress_bar=False
            )
            _embedding_cache.update(zip(missing, vectors))
        return np.vstack([_embedding_cache[t] for t in texts])

    vectorizer = TfidfVectorizer(
        strip_accents="unicode",
        lowercase=True,
        stop_words=SPANISH_STOPWORDS,
        ngram_range=(1, 2),
        sublinear_tf=True,
        token_pattern=r"(?u)#?\b\w\w+\b",
    )
    X = vectorizer.fit_transform(texts)
    n_components = min(100, X.shape[0] - 1, X.shape[1] - 1)
    if n_components >= 2:
        X = TruncatedSVD(n_components=n_components, random_state=seed).fit_transform(X)
    else:
        X = X.toarray()
    return normalize(X)


_embedding_cache: dict[str, np.ndarray] = {}


@lru_cache(maxsize=1)
def _sentence_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ImportError(
            'EMBEDDINGS=sentence-transformers requiere: pip install -e ".[embeddings]"'
        ) from e
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def cluster(
    X: np.ndarray, n_clusters: int | None = None, seed: int = 42, max_k: int = 8
) -> tuple[np.ndarray, np.ndarray]:
    """KMeans con k fijo, o elegido por silhouette si n_clusters es None.

    Devuelve (labels, centroides normalizados).
    """
    # Mensajes casi idénticos colapsan al mismo punto: no puede haber más clusters que puntos distintos
    n = len(np.unique(X.round(6), axis=0))
    if n_clusters is None:
        candidates = range(2, min(max_k, n - 1) + 1)
        if not candidates:
            return np.zeros(X.shape[0], dtype=int), normalize(X.mean(axis=0, keepdims=True))
        scored = []
        for k in candidates:
            labels = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(X)
            scored.append((silhouette_score(X, labels, metric="cosine"), -k))
        n_clusters = -max(scored)[1]

    n_clusters = max(1, min(n_clusters, n))
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=seed).fit(X)
    return km.labels_, normalize(km.cluster_centers_)


def assignment_margin(X: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    """Diferencia de similitud coseno entre el centroide más cercano y el segundo.

    Un margen bajo indica un mensaje ambiguo entre dos tópicos.
    """
    if centroids.shape[0] < 2:
        return np.ones(X.shape[0])
    sims = np.sort(X @ centroids.T, axis=1)
    return sims[:, -1] - sims[:, -2]


def top_terms(texts: list[str], labels: np.ndarray, n_terms: int = 5) -> dict[int, list[str]]:
    """Términos más característicos de cada cluster (c-TF-IDF simplificado)."""
    clusters = sorted(set(labels.tolist()))
    docs = [" ".join(t for t, lab in zip(texts, labels) if lab == c) for c in clusters]
    vectorizer = TfidfVectorizer(
        strip_accents="unicode", stop_words=SPANISH_STOPWORDS, token_pattern=r"(?u)#?\b\w\w+\b"
    )
    M = vectorizer.fit_transform(docs).toarray()
    vocab = np.array(vectorizer.get_feature_names_out())
    return {c: vocab[np.argsort(-M[i])[:n_terms]].tolist() for i, c in enumerate(clusters)}
