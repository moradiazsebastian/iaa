import numpy as np
import pytest

from foco_social.topic_models import _assign_outliers, _contiguous, fit_topics

TEXTS = [
    "el debate presidencial fue aburrido y sin propuestas",
    "nadie ganó el debate presidencial de anoche",
    "debate presidencial: los candidatos no respondieron",
    "otro debate presidencial sin ideas nuevas",
    "el voto electrónico es inseguro según expertos",
    "hay que auditar el voto electrónico ya",
    "voto electrónico rápido y fácil en mi provincia",
    "falló la máquina de voto electrónico en la escuela",
]


@pytest.mark.parametrize("method", ["kmeans", "lda"])
def test_fit_returns_one_label_and_confidence_per_text(settings, method):
    fit = fit_topics(TEXTS, 2, settings.model_copy(update={"topic_model": method}))
    assert fit.labels.shape == fit.confidence.shape == (len(TEXTS),)
    assert set(fit.labels.tolist()) == {0, 1}
    assert (fit.confidence >= 0).all()


@pytest.mark.parametrize("method", ["kmeans", "lda"])
def test_fit_is_deterministic(settings, method):
    s = settings.model_copy(update={"topic_model": method})
    assert (fit_topics(TEXTS, None, s).labels == fit_topics(TEXTS, None, s).labels).all()


def test_outliers_go_to_nearest_topic_with_zero_confidence():
    X = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9], [0.8, 0.2]])
    X = X / np.linalg.norm(X, axis=1, keepdims=True)
    labels, confidence = _assign_outliers(X, np.array([0, 0, 1, 1, -1]))
    assert labels[4] == labels[0]
    assert confidence[4] == 0 and (confidence[:4] > 0).all()


def test_contiguous_keeps_outliers():
    assert _contiguous(np.array([5, -1, 9, 5])).tolist() == [0, -1, 1, 0]


def test_bertopic_builds_hierarchy(settings, sample_csv):
    pytest.importorskip("bertopic")
    import pandas as pd

    texts = pd.read_csv(sample_csv)["text"].tolist()
    fit = fit_topics(texts, 3, settings.model_copy(update={"topic_model": "bertopic"}))
    assert len(set(fit.labels.tolist())) == 3
    if fit.sublabels is not None:
        # cada subtópico pertenece a un único tópico
        for sub in set(fit.sublabels.tolist()):
            assert len(set(fit.labels[fit.sublabels == sub].tolist())) == 1
