"""Métricas para comparar una clasificación en tópicos contra otra (manual o de otra corrida)."""

import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


def compare(pred: pd.Series, gold: pd.Series) -> dict:
    """Compara dos particiones de los mismos mensajes (índice = id del mensaje).

    - ARI / NMI: acuerdo entre particiones, sin importar los nombres de los tópicos.
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
        "ari": round(adjusted_rand_score(gold, pred), 4),
        "nmi": round(normalized_mutual_info_score(gold, pred), 4),
        "matched_accuracy": round(matched / len(common), 4),
        "matching": {table.index[r]: table.columns[c] for r, c in zip(rows, cols)},
        "n_pred": table.shape[0],
        "n_gold": table.shape[1],
    }


def level(paths: pd.Series, depth: int) -> pd.Series:
    """Recorta paths jerárquicos ('2.1.3') a una profundidad dada ('2.1')."""
    return paths.map(lambda p: ".".join(p.split(".")[:depth]) if p else "(sin tópico)")
