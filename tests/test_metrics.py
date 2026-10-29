import pandas as pd

from foco_social.evaluation.metrics import compare, level


def test_identical_partitions_with_different_names_score_perfect():
    gold = pd.Series(["a", "a", "b", "b", "c"], index=list("12345"))
    pred = pd.Series(["2", "2", "1", "1", "3"], index=list("12345"))
    m = compare(pred, gold)
    assert m["ari"] == 1.0 and m["matched_accuracy"] == 1.0
    assert m["matching"] == {"2": "a", "1": "b", "3": "c"}


def test_level_truncates_paths():
    paths = pd.Series(["1.2.3", "2", ""])
    assert level(paths, 2).tolist() == ["1.2", "2", "(sin tópico)"]
