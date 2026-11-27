"""Métricas de evaluación y benchmark para Foco Social.

Organizadas según las 4 suites del entorno de evaluación:
- Suite A (Relevancia y Filtrado de Ruido): `evaluate_relevance`
- Suite B (Partición Extrínseca e Intrínseca para BERTopic/Embeddings): `compare`, `evaluate`,
  `evaluate_intrinsic`, `topic_diversity`, `topic_coherence_npmi`
- Suite C (Valor Agregado del Agente / LLM): `evaluate_reassignment_delta`, `evaluate_label_quality`
- Suite D (Operativa y Reproducibilidad): `compare` inter-corrida + estadísticas de ejecución.
"""

import math
import re
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from scipy.optimize import linear_sum_assignment
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import (
    adjusted_rand_score,
    completeness_score,
    f1_score,
    homogeneity_score,
    normalized_mutual_info_score,
    precision_score,
    recall_score,
    silhouette_score,
    v_measure_score,
)

from foco_social.clustering import SPANISH_STOPWORDS, top_terms

if TYPE_CHECKING:
    from foco_social.llm import LLM


# --- Suite B (Extrínsecas): Acuerdo entre particiones -------------------------


def compare(pred: pd.Series, gold: pd.Series) -> dict:
    """Compara dos particiones de los mismos mensajes (índice = id del mensaje).

    - ARI / NMI: acuerdo entre particiones, sin importar los nombres de los tópicos.
    - homogeneity / completeness / v_measure: pureza y completitud (clave cuando K es automático).
    - matched_accuracy: emparejando 1 a 1 tópicos predichos y reales (Hungarian),
      proporción de mensajes que caen en el par correcto.
    """
    common = pred.index.intersection(gold.index)
    pred, gold = pred.loc[common].astype(str), gold.loc[common].astype(str)
    if len(common) == 0:
        return {"n": 0}

    table = pd.crosstab(pred, gold)
    rows, cols = linear_sum_assignment(-table.to_numpy())
    matched = int(table.to_numpy()[rows, cols].sum())
    return {
        "n": len(common),
        "ari": round(float(adjusted_rand_score(gold, pred)), 4),
        "nmi": round(float(normalized_mutual_info_score(gold, pred)), 4),
        "homogeneity": round(float(homogeneity_score(gold, pred)), 4),
        "completeness": round(float(completeness_score(gold, pred)), 4),
        "v_measure": round(float(v_measure_score(gold, pred)), 4),
        "matched_accuracy": round(matched / len(common), 4),
        "matching": {table.index[r]: table.columns[c] for r, c in zip(rows, cols)},
        "n_pred": int(table.shape[0]),
        "n_gold": int(table.shape[1]),
    }


def evaluate(
    pred: pd.Series, gold: pd.DataFrame, depth: int, names: dict[str, str] | None = None
) -> dict:
    """Métricas de tópicos (y subtópicos si corresponde) contra las etiquetas manuales.

    `pred`: path del tópico de cada mensaje (índice = id). `gold`: columnas topic / subtopic
    (y opcionalmente `is_relevant`). Si `gold` incluye mensajes con `topic == '(ruido)'` o
    `is_relevant == False`, las métricas de partición se calculan sobre los mensajes relevantes.
    `names`: {path: nombre}, para que el emparejamiento se lea con nombres.
    """
    if "is_relevant" in gold.columns:
        rel_mask = gold["is_relevant"].astype(bool)
    else:
        rel_mask = gold["topic"].astype(str) != "(ruido)"

    gold_rel = gold.loc[rel_mask]
    metrics = {"topics": compare(level(pred, 1), gold_rel["topic"])}
    if "subtopic" in gold_rel.columns and gold_rel["subtopic"].notna().any() and depth >= 2:
        gold_sub = gold_rel["topic"] + " / " + gold_rel["subtopic"].fillna("")
        metrics["subtopics"] = compare(level(pred, 2), gold_sub)
    names = names or {}
    for m in metrics.values():
        if "matching" in m:
            m["matching"] = {f"{k} {names.get(k, '')}".strip(): v for k, v in m["matching"].items()}

    if not rel_mask.all():
        pred_rel = pd.Series(False, index=gold.index)
        active = pred.reindex(gold.index).fillna("")
        pred_rel.loc[(active != "") & (active != "(sin tópico)") & (active != "(ruido)")] = True
        metrics["relevance"] = evaluate_relevance(pred_rel, rel_mask, topic_assignments=active)

    return metrics


def level(paths: pd.Series, depth: int) -> pd.Series:
    """Recorta paths jerárquicos ('2.1.3') a una profundidad dada ('2.1')."""
    return paths.map(lambda p: ".".join(p.split(".")[:depth]) if p else "(sin tópico)")


# --- Suite A: Clasificación de Relevancia y Filtrado de Ruido -----------------


def evaluate_relevance(
    pred_relevant: pd.Series,
    gold_relevant: pd.Series,
    topic_assignments: pd.Series | None = None,
) -> dict:
    """Evalúa qué tan bien el filtro/agente separa mensajes relevantes del ruido colado.

    - `precision`, `recall`, `f1`, `accuracy`: métricas binarias sobre `is_relevant`.
    - `noise_leakage_rate`: proporción del ruido real (`gold_relevant=False`) que terminó
      asignado a algún tópico final.
    - `false_drop_rate`: proporción de mensajes relevantes reales que fueron descartados (`1 - recall`).
    """
    common = pred_relevant.index.intersection(gold_relevant.index)
    if len(common) == 0:
        return {"n": 0}
    p = pred_relevant.loc[common].astype(bool)
    g = gold_relevant.loc[common].astype(bool)

    tp = int((p & g).sum())
    fp = int((p & ~g).sum())
    tn = int((~p & ~g).sum())
    fn = int((~p & g).sum())
    n_noise = int((~g).sum())
    n_rel = int(g.sum())

    if topic_assignments is not None:
        assigned = topic_assignments.reindex(common).fillna("")
        has_topic = (assigned != "") & (assigned != "(sin tópico)") & (assigned != "(ruido)")
        leaked = int((has_topic & ~g).sum())
    else:
        leaked = fp

    return {
        "n": len(common),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(float(precision_score(g, p, zero_division=0)), 4),
        "recall": round(float(recall_score(g, p, zero_division=0)), 4),
        "f1": round(float(f1_score(g, p, zero_division=0)), 4),
        "accuracy": round((tp + tn) / len(common), 4),
        "noise_leakage_rate": round(leaked / n_noise, 4) if n_noise > 0 else 0.0,
        "false_drop_rate": round(fn / n_rel, 4) if n_rel > 0 else 0.0,
    }


# --- Suite B (Intrínsecas): Calidad de Tópicos sin Etiquetas Manuales ---------


def topic_diversity(texts: list[str], labels: np.ndarray, top_n: int = 10) -> float:
    """Proporción de palabras únicas entre los `top_n` términos c-TF-IDF de todos los tópicos.

    Rango [0, 1]: 1.0 indica que ningún tópico repite palabras clave de otro (alta diversidad);
    valores bajos indican tópicos redundantes o solapados.
    """
    labels = np.asarray(labels)
    valid = labels != -1
    if valid.sum() == 0:
        return 0.0
    filtered_texts = [t for t, v in zip(texts, valid) if v]
    filtered_labels = labels[valid]
    if len(set(filtered_labels.tolist())) < 1:
        return 0.0
    try:
        terms_by_cluster = top_terms(filtered_texts, filtered_labels, n_terms=top_n)
    except ValueError:
        return 0.0
    all_terms = [w for words in terms_by_cluster.values() for w in words]
    if not all_terms:
        return 0.0
    return round(len(set(all_terms)) / len(all_terms), 4)


def topic_coherence_npmi(texts: list[str], labels: np.ndarray, top_n: int = 5) -> float:
    """Coherencia semántica NPMI (Normalized Pointwise Mutual Information) sobre co-ocurrencia.

    Rango [-1, 1]: valores positivos altos indican que las palabras principales de cada tópico
    tienden a aparecer juntas en los mismos mensajes.
    """
    labels = np.asarray(labels)
    valid = labels != -1
    filtered_texts = [t for t, v in zip(texts, valid) if v]
    filtered_labels = labels[valid]
    if len(filtered_texts) < 2 or len(set(filtered_labels.tolist())) < 1:
        return 0.0

    try:
        terms_by_cluster = top_terms(filtered_texts, filtered_labels, n_terms=top_n)
        vectorizer = CountVectorizer(
            strip_accents="unicode",
            lowercase=True,
            stop_words=SPANISH_STOPWORDS,
            token_pattern=r"(?u)#?\b\w\w+\b",
            binary=True,
        )
        X = vectorizer.fit_transform(filtered_texts)
    except ValueError:
        return 0.0

    vocab = {w: idx for idx, w in enumerate(vectorizer.get_feature_names_out())}
    n_docs = float(X.shape[0])
    eps = 1e-12

    cluster_scores = []
    for words in terms_by_cluster.values():
        idxs = [vocab[w] for w in words if w in vocab]
        if len(idxs) < 2:
            continue
        pair_scores = []
        cols = [X[:, i].toarray().ravel() for i in idxs]
        for a in range(len(cols)):
            for b in range(a + 1, len(cols)):
                c_i = int(cols[a].sum())
                c_j = int(cols[b].sum())
                c_ij = int((cols[a] & cols[b]).sum())
                if c_ij == 0 or c_i == 0 or c_j == 0:
                    pair_scores.append(-1.0)
                else:
                    p_i = c_i / n_docs
                    p_j = c_j / n_docs
                    p_ij = c_ij / n_docs
                    pmi = math.log((p_ij + eps) / (p_i * p_j + eps))
                    denom = -math.log(p_ij + eps)
                    npmi = pmi / denom if denom > 0 else 1.0
                    pair_scores.append(max(-1.0, min(1.0, npmi)))
        if pair_scores:
            cluster_scores.append(float(np.mean(pair_scores)))

    if not cluster_scores:
        return 0.0
    return round(float(np.mean(cluster_scores)), 4)


def evaluate_intrinsic(
    texts: list[str],
    labels: np.ndarray,
    embeddings: np.ndarray | None = None,
    raw_outlier_rate: float | None = None,
    top_n: int = 10,
) -> dict:
    """Métricas intrínsecas (sin etiquetas manuales) para evaluar BERTopic y embeddings."""
    labels = np.asarray(labels)
    valid = labels != -1
    unique_clusters = set(labels[valid].tolist())
    outlier_rate = (
        float(raw_outlier_rate)
        if raw_outlier_rate is not None
        else float((labels == -1).mean())
        if len(labels)
        else 0.0
    )

    sil = None
    if embeddings is not None and valid.sum() >= 3 and 2 <= len(unique_clusters) < valid.sum():
        sil = round(
            float(silhouette_score(embeddings[valid], labels[valid], metric="cosine")),
            4,
        )

    return {
        "n_tweets": len(texts),
        "n_topics": len(unique_clusters),
        "outlier_rate": round(outlier_rate, 4),
        "topic_diversity": topic_diversity(texts, labels, top_n=top_n),
        "topic_coherence_npmi": topic_coherence_npmi(texts, labels, top_n=min(5, top_n)),
        "silhouette_cosine": sil,
    }


# --- Suite C: Valor Agregado del Agente / LLM (Ablation y Etiquetas) ----------


def evaluate_reassignment_delta(pre_pred: pd.Series, post_pred: pd.Series, gold: pd.Series) -> dict:
    """Mide cuánto mejora (o empeora) la partición tras la reasignación de ambiguos del LLM."""
    common = pre_pred.index.intersection(post_pred.index).intersection(gold.index)
    if len(common) == 0:
        return {"n": 0}
    pre_s = pre_pred.loc[common].astype(str)
    post_s = post_pred.loc[common].astype(str)
    gold_s = gold.loc[common].astype(str)

    pre_m = compare(pre_s, gold_s)
    post_m = compare(post_s, gold_s)
    changed = int((pre_s != post_s).sum())

    return {
        "n": len(common),
        "n_reassigned": changed,
        "reassigned_ratio": round(changed / len(common), 4),
        "delta_ari": round(post_m["ari"] - pre_m["ari"], 4),
        "delta_nmi": round(post_m["nmi"] - pre_m["nmi"], 4),
        "delta_v_measure": round(post_m["v_measure"] - pre_m["v_measure"], 4),
        "delta_matched_accuracy": round(post_m["matched_accuracy"] - pre_m["matched_accuracy"], 4),
        "pre": pre_m,
        "post": post_m,
    }


class TopicJudgeScore(BaseModel):
    path: str = Field(description="Identificador o ruta del tópico evaluado")
    faithfulness: int = Field(
        ge=1, le=5, description="1 a 5: ¿El nombre y descripción reflejan fielmente los mensajes?"
    )
    specificity: int = Field(
        ge=1,
        le=5,
        description="1 a 5: ¿El nombre es específico del evento (nombres/hechos) y no genérico?",
    )
    exclusivity: int = Field(
        ge=1, le=5, description="1 a 5: ¿Se distingue claramente de los demás tópicos hermanos?"
    )


class TopicJudgeResult(BaseModel):
    scores: list[TopicJudgeScore]


JUDGE_SYSTEM = """Sos un evaluador experto de modelos de tópicos en redes sociales (LLM-as-a-Judge).
Recibís una lista de tópicos generados por un agente (nombre, descripción y muestra de mensajes).
Evaluá cada tópico del 1 al 5 en tres criterios:
- faithfulness (fidelidad): ¿los mensajes de muestra realmente hablan de lo que dice el tópico?
- specificity (especificidad): ¿el título captura actores/hechos concretos en vez de frases vagas?
- exclusivity (exclusividad): ¿el tópico es distinguible y no se superpone con los otros tópicos?"""


def evaluate_label_quality(
    topics: list[dict],
    texts_by_topic: dict[str, list[str]],
    llm: "LLM | None" = None,
) -> dict:
    """Evalúa la calidad semántica de los nombres y descripciones de los tópicos.

    Calcula siempre indicadores estructurales/heurísticos (distinción entre títulos, longitud,
    ausencia de fallback crudo y cobertura léxica) y, si se provee un `llm` habilitado, suma
    el puntaje 1-5 de *LLM-as-a-Judge* (`faithfulness`, `specificity`, `exclusivity`).
    """
    if not topics:
        return {"n_topics": 0}

    token_sets = []
    lengths = []
    non_fallback = 0
    lexical_overlaps = []

    for t in topics:
        path = str(t.get("path", ""))
        name = str(t.get("name", ""))
        desc = str(t.get("description", ""))
        words = [
            w
            for w in re.findall(r"[a-záéíóúñü0-9]{3,}", f"{name} {desc}".lower())
            if w not in SPANISH_STOPWORDS
        ]
        name_words = [
            w
            for w in re.findall(r"[a-záéíóúñü0-9]{3,}", name.lower())
            if w not in SPANISH_STOPWORDS
        ]
        token_sets.append(set(name_words))
        lengths.append(len(name.split()))
        if not desc.startswith("Términos:") and "," not in name:
            non_fallback += 1

        sample_texts = " ".join(texts_by_topic.get(path, [])).lower()
        if words and sample_texts:
            hits = sum(1 for w in set(words) if w in sample_texts)
            lexical_overlaps.append(hits / len(set(words)))

    # Distinción promedio entre pares de títulos (1 - Jaccard)
    pairwise_dist = []
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            union = token_sets[i] | token_sets[j]
            inter = token_sets[i] & token_sets[j]
            jaccard = len(inter) / len(union) if union else 0.0
            pairwise_dist.append(1.0 - jaccard)

    result = {
        "n_topics": len(topics),
        "avg_name_words": round(float(np.mean(lengths)), 2) if lengths else 0.0,
        "non_fallback_rate": round(non_fallback / len(topics), 4),
        "label_distinctness": round(float(np.mean(pairwise_dist)), 4) if pairwise_dist else 1.0,
        "lexical_grounding": round(float(np.mean(lexical_overlaps)), 4)
        if lexical_overlaps
        else 0.0,
    }

    if llm is not None and llm.enabled:
        lines = []
        for t in topics:
            path = str(t.get("path", ""))
            lines.append(f"## path={path} | nombre={t.get('name')} | desc={t.get('description')}")
            for s in texts_by_topic.get(path, [])[:5]:
                lines.append(f"- {' '.join(str(s).split())[:160]}")
        judged = llm.structured(TopicJudgeResult, JUDGE_SYSTEM, "\n".join(lines))
        if judged.scores:
            result["judge_faithfulness"] = round(
                float(np.mean([s.faithfulness for s in judged.scores])), 2
            )
            result["judge_specificity"] = round(
                float(np.mean([s.specificity for s in judged.scores])), 2
            )
            result["judge_exclusivity"] = round(
                float(np.mean([s.exclusivity for s in judged.scores])), 2
            )

    return result
