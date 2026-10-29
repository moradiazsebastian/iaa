import re

import pytest

from foco_social.llm import LLM
from foco_social.runner import run_analysis, save_run
from foco_social.schemas import Assignment, Assignments, SearchPlan, TopicLabel, TopicLabels

KEYWORDS = ["debate", "encuesta", "fraude", "voto", "inflacion", "candidato", "campaña"]


class StubLLM(LLM):
    """Simula al LLM: respuestas fijas con la forma de cada esquema, sin llamar a la red."""

    def __init__(self, settings):
        super().__init__(settings)
        self.enabled = True
        self.requests = []

    def structured(self, schema, system, user):
        self.requests.append(schema)
        if schema is SearchPlan:
            return SearchPlan(keywords=KEYWORDS)
        if schema is TopicLabels:
            ids = [int(i) for i in re.findall(r"cluster_id=(\d+)", user)]
            return TopicLabels(
                topics=[
                    TopicLabel(cluster_id=i, name=f"Tópico {i}", description="desc") for i in ids
                ]
            )
        if schema is Assignments:
            n = len(re.findall(r"^\[\d+\]", user, flags=re.MULTILINE))
            first = int(re.search(r"cluster_id=(\d+)", user).group(1))
            return Assignments(
                assignments=[Assignment(tweet_index=i, cluster_id=first) for i in range(n)]
            )
        raise AssertionError(schema)


def test_offline_run_assigns_every_tweet(settings):
    result = run_analysis(settings, theme="elecciones", keywords=KEYWORDS, n_topics=4, depth=2)
    assert result.stats["n_tweets"] > 0
    assert len(result.assignments) == result.stats["n_tweets"]

    level1 = [t for t in result.topics if t.level == 1]
    assert len(level1) == 4
    assert sum(t.n_tweets for t in level1) == result.stats["n_tweets"]
    assert sum(t.share_of_total for t in level1) == pytest.approx(1.0)

    for parent in level1:
        children = [t for t in result.topics if t.path.startswith(parent.path + ".")]
        if children:
            assert sum(c.n_tweets for c in children) == parent.n_tweets


def test_llm_plans_labels_and_reassigns(settings):
    llm = StubLLM(settings)
    result = run_analysis(settings, theme="elecciones", n_topics=3, depth=1, llm=llm)
    assert result.keywords[0] == "elecciones" and "debate" in result.keywords
    assert all(t.name.startswith("Tópico") for t in result.topics)
    assert {SearchPlan, TopicLabels, Assignments} <= set(llm.requests)


def test_save_run_writes_outputs(settings, tmp_path):
    result = run_analysis(settings, theme="elecciones", keywords=KEYWORDS, depth=1)
    run_dir = save_run(result, settings, tmp_path / "run")
    for name in ["config.json", "topics.json", "assignments.csv", "report.md"]:
        assert (run_dir / name).exists()
