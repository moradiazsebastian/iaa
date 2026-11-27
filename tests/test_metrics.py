import numpy as np
import pandas as pd

from foco_social.evaluation.boca import check_relevance, classify_riestra, parse_author
from foco_social.evaluation.metrics import (
    compare,
    evaluate_intrinsic,
    evaluate_label_quality,
    evaluate_reassignment_delta,
    evaluate_relevance,
    level,
    topic_coherence_npmi,
    topic_diversity,
)


def test_identical_partitions_with_different_names_score_perfect():
    gold = pd.Series(["a", "a", "b", "b", "c"], index=list("12345"))
    pred = pd.Series(["2", "2", "1", "1", "3"], index=list("12345"))
    m = compare(pred, gold)
    assert m["ari"] == 1.0 and m["matched_accuracy"] == 1.0
    assert m["v_measure"] == 1.0 and m["homogeneity"] == 1.0 and m["completeness"] == 1.0
    assert m["matching"] == {"2": "a", "1": "b", "3": "c"}


def test_level_truncates_paths():
    paths = pd.Series(["1.2.3", "2", ""])
    assert level(paths, 2).tolist() == ["1.2", "2", "(sin tópico)"]


def test_evaluate_relevance_and_noise_leakage():
    gold = pd.Series([True, True, False, False], index=["1", "2", "3", "4"])
    pred = pd.Series([True, False, True, False], index=["1", "2", "3", "4"])
    topics = pd.Series(["1.1", "", "2.1", "(ruido)"], index=["1", "2", "3", "4"])
    m = evaluate_relevance(pred, gold, topic_assignments=topics)
    assert m["tp"] == 1 and m["fp"] == 1 and m["tn"] == 1 and m["fn"] == 1
    assert m["precision"] == 0.5 and m["recall"] == 0.5 and m["f1"] == 0.5
    assert m["noise_leakage_rate"] == 0.5
    assert m["false_drop_rate"] == 0.5


def test_intrinsic_metrics_diversity_and_coherence():
    texts = [
        "gol de di lollo tras centro de paredes en boca",
        "cabezazo de di lollo y asistencia de paredes para el triunfo",
        "di lollo convirtió de cabeza luego del tiro libre de paredes",
        "atajadón de marchesín para salvar el arco de boca",
        "marchesín tapó el mano a mano sobre la hora en el arco",
        "gran atajada del arquero marchesín en el segundo tiempo",
    ]
    labels = np.array([0, 0, 0, 1, 1, 1])
    div = topic_diversity(texts, labels, top_n=4)
    coh = topic_coherence_npmi(texts, labels, top_n=4)
    intr = evaluate_intrinsic(texts, labels, raw_outlier_rate=0.15, top_n=4)
    assert 0.5 <= div <= 1.0
    assert -1.0 <= coh <= 1.0
    assert intr["outlier_rate"] == 0.15
    assert intr["n_topics"] == 2


def test_reassignment_delta_tracks_llm_improvement():
    gold = pd.Series(["A", "A", "B", "B"], index=["1", "2", "3", "4"])
    pre = pd.Series(["0", "1", "1", "1"], index=["1", "2", "3", "4"])
    post = pd.Series(["0", "0", "1", "1"], index=["1", "2", "3", "4"])
    delta = evaluate_reassignment_delta(pre, post, gold)
    assert delta["n_reassigned"] == 1
    assert delta["delta_ari"] > 0
    assert delta["post"]["matched_accuracy"] == 1.0


def test_label_quality_heuristics():
    topics = [
        {"path": "1", "name": "Gol de Di Lollo", "description": "Cabezazo tras centro de Paredes"},
        {"path": "2", "name": "Atajadas de Marchesín", "description": "Tapadas clave del arquero"},
    ]
    texts_by_topic = {
        "1": ["Gol de Di Lollo de cabeza tras gran centro de Paredes"],
        "2": ["Tremenda atajada del arquero Marchesín en el final"],
    }
    q = evaluate_label_quality(topics, texts_by_topic)
    assert q["n_topics"] == 2
    assert q["non_fallback_rate"] == 1.0
    assert q["label_distinctness"] == 1.0
    assert q["lexical_grounding"] > 0.5


def test_boca_ground_truth_helpers():
    user, followers = parse_author("{'userName': 'DiarioXeneize', 'followers': 85000}")
    assert user == "DiarioXeneize" and followers == 85000
    is_rel, _ = check_relevance("Gran anticipo de Di Lollo y gana Boca", "DiarioXeneize", "Riestra")
    assert is_rel is True
    is_rel_noise, reason = check_relevance(
        "New England headed to the Super Bowl", "espn", "Riestra"
    )
    assert is_rel_noise is False and "NBA/NFL" in reason
    top, sub = classify_riestra("Centro de Paredes y cabezazo de Di Lollo para el 1-0 de Boca")
    assert "Di Lollo" in top and "Paredes" in sub
