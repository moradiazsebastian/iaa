import pytest

from foco_social.config import Settings
from foco_social.evaluation.synthetic import generate


@pytest.fixture(scope="session")
def sample_csv(tmp_path_factory):
    path = tmp_path_factory.mktemp("data") / "tweets.csv"
    generate(per_subtopic=20, seed=0).to_csv(path, index=False)
    return path


@pytest.fixture
def settings(sample_csv, tmp_path):
    return Settings(
        _env_file=None,
        llm_provider="none",
        data_path=sample_csv,
        runs_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
    )
