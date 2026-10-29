import numpy as np

from foco_social.clustering import assignment_margin, cluster, embed, top_terms

TEXTS = [
    "el debate presidencial fue aburrido",
    "nadie ganó el debate presidencial",
    "debate presidencial sin propuestas",
    "el voto electrónico es inseguro",
    "auditar el voto electrónico ya",
    "voto electrónico rápido y fácil",
]


def test_embed_rows_are_unit_norm():
    X = embed(TEXTS)
    assert np.allclose(np.linalg.norm(X, axis=1), 1.0)


def test_cluster_separates_obvious_groups():
    labels, centroids = cluster(embed(TEXTS), n_clusters=2)
    assert len(set(labels[:3])) == 1 and len(set(labels[3:])) == 1
    assert labels[0] != labels[3]
    assert centroids.shape[0] == 2


def test_cluster_is_deterministic():
    X = embed(TEXTS)
    assert (cluster(X, seed=1)[0] == cluster(X, seed=1)[0]).all()


def test_margin_and_terms():
    X = embed(TEXTS)
    labels, centroids = cluster(X, n_clusters=2)
    assert assignment_margin(X, centroids).shape == (len(TEXTS),)
    terms = top_terms(TEXTS, labels)
    assert any("debate" in t for t in terms[labels[0]])
