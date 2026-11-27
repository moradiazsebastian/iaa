"""Orquestador de las 4 Suites del Benchmark (Relevancia, Embeddings en BERTopic, Ablation LLM y Operativa)."""

import time

import pandas as pd

from foco_social.clustering import embed
from foco_social.config import Settings
from foco_social.evaluation.metrics import (
    compare,
    evaluate,
    evaluate_intrinsic,
    evaluate_label_quality,
    evaluate_relevance,
)
from foco_social.sources.static import normalize
from foco_social.topic_models import fit_presplit, fit_topics

DEFAULT_EMBEDDING_MODELS = [
    "paraphrase-multilingual-MiniLM-L12-v2",
    "intfloat/multilingual-e5-small",
    "paraphrase-multilingual-mpnet-base-v2",
]


# --- Suite A: Estrategias de Clasificación de Relevancia ----------------------


def keyword_relevance_filter(df: pd.DataFrame, keywords: list[str]) -> pd.Series:
    """Filtro base de relevancia: marca como relevante si el texto contiene alguna keyword."""
    norm_kw = [normalize(k).strip() for k in keywords if k.strip()]
    if not norm_kw:
        return pd.Series(False, index=df.index)
    texts = df["text"].fillna("").astype(str).map(normalize)
    mask = texts.map(lambda t: any(k in t for k in norm_kw))
    return pd.Series(mask.to_numpy(), index=df.index, dtype=bool)


def context_relevance_filter(
    df: pd.DataFrame,
    keywords: list[str],
    dedicated_authors: set[str] | None = None,
    min_words: int = 2,
) -> pd.Series:
    """Filtro híbrido (autor dedicado + keywords + descarte de mensajes vacíos/links)."""
    import re

    dedicated_authors = dedicated_authors or {
        "DiarioXeneize",
        "la12tuittera",
        "lamitadmas1",
        "CABJ_English",
        "bocanet12",
        "ElEspectadorXen",
        "SANGREXENEIZE",
        "equipoatodoboca",
        "PlanetaBoca",
        "HormigaXeneize",
        "BocaPasionTotal",
        "yosigoaboca",
        "PuntoBocaRadio",
        "BocaTVPlay",
        "LocosxBoca",
        "EternoBoca12",
        "Cadena_Xeneize",
        "RinconDeBoca",
        "Nicoambrogi",
        "LuisFregossi",
        "FerBurruso",
    }
    kw_match = keyword_relevance_filter(df, keywords)
    clean_words = (
        df["text"].fillna("").astype(str).map(lambda t: len(re.sub(r"https?://\S+", "", t).split()))
    )
    has_text = clean_words >= min_words
    is_dedicated = (
        df["author"].isin(dedicated_authors)
        if "author" in df.columns
        else pd.Series(False, index=df.index)
    )
    return (has_text & (kw_match | is_dedicated)).astype(bool)


def embedding_relevance_filter(
    df: pd.DataFrame,
    query_description: str,
    threshold: float = 0.25,
    method: str = "tfidf",
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    seed: int = 42,
) -> pd.Series:
    """Filtro de relevancia semántica por similitud coseno contra la descripción del evento."""
    import re

    texts = df["text"].fillna("").astype(str).tolist()
    clean_words = [len(re.sub(r"https?://\S+", "", t).split()) for t in texts]
    all_texts = [query_description] + texts
    vectors = embed(all_texts, method=method, seed=seed, model_name=model_name)
    query_vec = vectors[0]
    doc_vecs = vectors[1:]
    sims = doc_vecs @ query_vec
    relevant = [(w >= 2 and float(s) >= threshold) for w, s in zip(clean_words, sims)]
    return pd.Series(relevant, index=df.index, dtype=bool)


def benchmark_relevance_filters(
    df: pd.DataFrame,
    theme: str,
    keywords: list[str],
    embedding_method: str = "tfidf",
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> pd.DataFrame:
    """Evalúa distintas estrategias de filtrado de relevancia contra `is_relevant` del Ground Truth."""
    if "is_relevant" not in df.columns:
        raise ValueError("El DataFrame debe incluir la columna booleana 'is_relevant'.")

    indexed = df.set_index("id") if "id" in df.columns else df.copy()
    gold = indexed["is_relevant"].astype(bool)

    strategies = {
        "sin_filtro (todo relevante)": pd.Series(True, index=indexed.index),
        "keywords_estricto": keyword_relevance_filter(indexed, keywords),
        "contexto_autor_y_keywords": context_relevance_filter(indexed, keywords),
        f"similitud_{embedding_method}": embedding_relevance_filter(
            indexed,
            query_description=f"{theme} {' '.join(keywords)}",
            threshold=0.12 if embedding_method == "tfidf" else 0.35,
            method=embedding_method,
            model_name=embedding_model,
        ),
    }

    rows = []
    for name, pred in strategies.items():
        m = evaluate_relevance(pred, gold)
        rows.append({"estrategia": name, **m})
    return pd.DataFrame(rows)


# --- Suite B: Benchmark de Modelos de Embeddings en BERTopic ------------------


def benchmark_embeddings(
    df: pd.DataFrame,
    models: list[str] | None = None,
    n_topics: int | None = None,
    n_subtopics: int | None = None,
    depth: int = 2,
    topic_model: str = "bertopic",
    settings: Settings | None = None,
) -> pd.DataFrame:
    """Compara modelos de embeddings sobre el mismo conjunto de mensajes relevantes.

    Reporta tanto métricas extrínsecas contra `topic`/`subtopic` (`ARI`, `NMI`, `v_measure`,
    `matched_accuracy`) como métricas intrínsecas (`outlier_rate`, `topic_diversity`,
    `topic_coherence_npmi`, `silhouette_cosine`, `seconds`).
    """
    settings = settings or Settings(_env_file=None, llm_provider="none")
    models = models or DEFAULT_EMBEDDING_MODELS

    rel_df = df[df["is_relevant"]].copy() if "is_relevant" in df.columns else df.copy()
    rel_df["id"] = rel_df["id"].astype(str)
    rel_df = rel_df.set_index("id")
    texts = rel_df["text"].fillna("").astype(str).tolist()
    ids = rel_df.index.tolist()

    has_gold = "topic" in rel_df.columns
    has_subgold = has_gold and "subtopic" in rel_df.columns and rel_df["subtopic"].notna().any()
    gold_sub = (rel_df["topic"] + " / " + rel_df["subtopic"].fillna("")) if has_subgold else None

    rows = []
    for model_name in models:
        is_tfidf = model_name.lower() == "tfidf"
        s = settings.model_copy(
            update={
                "topic_model": "kmeans" if is_tfidf else topic_model,
                "embeddings": "tfidf" if is_tfidf else "sentence-transformers",
                "embedding_model": model_name,
            }
        )
        t0 = time.perf_counter()
        try:
            X = embed(texts, method=s.embeddings, seed=s.seed, model_name=model_name)
            fit = fit_topics(texts, n_topics, s)
        except ImportError as e:
            rows.append({"embedding_model": model_name, "método": s.topic_model, "error": str(e)})
            continue
        elapsed = round(time.perf_counter() - t0, 2)

        intrinsic = evaluate_intrinsic(
            texts,
            fit.labels,
            embeddings=X,
            raw_outlier_rate=fit.outlier_rate,
        )
        row: dict = {
            "embedding_model": model_name,
            "método": s.topic_model,
            "mensajes": len(texts),
            "tópicos": intrinsic["n_topics"],
            "outlier_rate": intrinsic["outlier_rate"],
            "diversity": intrinsic["topic_diversity"],
            "coherence_npmi": intrinsic["topic_coherence_npmi"],
            "silhouette": intrinsic["silhouette_cosine"],
        }

        if has_gold:
            pred_lvl1 = pd.Series([str(lbl) for lbl in fit.labels], index=ids)
            ext1 = compare(pred_lvl1, rel_df["topic"])
            row.update(
                {
                    "ARI": ext1["ari"],
                    "NMI": ext1["nmi"],
                    "V-Measure": ext1["v_measure"],
                    "acc": ext1["matched_accuracy"],
                }
            )

            if has_subgold and depth >= 2:
                sub_paths = _compute_subtopic_paths(texts, ids, fit, n_subtopics, s)
                ext2 = compare(sub_paths, gold_sub)
                row.update(
                    {
                        "ARI sub": ext2["ari"],
                        "NMI sub": ext2["nmi"],
                        "V-Measure sub": ext2["v_measure"],
                        "acc sub": ext2["matched_accuracy"],
                    }
                )

        row["segundos"] = elapsed
        rows.append(row)

    return pd.DataFrame(rows)


def _compute_subtopic_paths(
    texts: list[str],
    ids: list[str],
    fit,
    n_subtopics: int | None,
    settings: Settings,
) -> pd.Series:
    """Construye los paths `topico.subtopico` de nivel 2 para evaluar la jerarquía."""
    paths = {i: str(lbl) for i, lbl in zip(ids, fit.labels)}
    for parent_id in sorted(set(fit.labels.tolist())):
        idx = [j for j, lbl in enumerate(fit.labels) if lbl == parent_id]
        if len(idx) < 12:
            continue
        sub_texts = [texts[j] for j in idx]
        if fit.sublabels is not None:
            sub_fit = fit_presplit(
                sub_texts, [int(fit.sublabels[j]) for j in idx], n_subtopics, settings
            )
        else:
            sub_fit = fit_topics(sub_texts, n_subtopics, settings)
        if sub_fit is not None and len(set(sub_fit.labels.tolist())) >= 2:
            for j, sub_lbl in zip(idx, sub_fit.labels):
                paths[ids[j]] = f"{parent_id}.{sub_lbl}"
    return pd.Series(paths)


__all__ = [
    "DEFAULT_EMBEDDING_MODELS",
    "benchmark_embeddings",
    "benchmark_relevance_filters",
    "context_relevance_filter",
    "embedding_relevance_filter",
    "evaluate",
    "evaluate_label_quality",
    "keyword_relevance_filter",
]
