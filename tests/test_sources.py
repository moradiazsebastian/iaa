from datetime import timedelta

import pytest

from foco_social.sources import ReplaySource, StaticSource


def test_search_ignores_case_and_accents(sample_csv):
    source = StaticSource(sample_csv)
    with_accent = source.search(["INFLACIÓN"])
    without_accent = source.search(["inflacion"])
    assert with_accent and [t.id for t in with_accent] == [t.id for t in without_accent]
    assert all("inflaci" in t.text.lower() for t in with_accent)


def test_search_respects_limit_and_orders_by_engagement(sample_csv):
    tweets = StaticSource(sample_csv).search(["debate"], limit=5)
    assert len(tweets) == 5
    engagement = [t.likes + t.retweets for t in tweets]
    assert engagement == sorted(engagement, reverse=True)


def test_sql_is_read_only(sample_csv):
    source = StaticSource(sample_csv)
    assert source.sql("SELECT count(*) AS n FROM tweets")["n"][0] > 0
    with pytest.raises(ValueError):
        source.sql("DROP VIEW tweets")


def test_labels_available_for_evaluation(sample_csv):
    labels = StaticSource(sample_csv).labels()
    assert {"topic", "subtopic"} <= set(labels.columns)


def test_replay_only_shows_past_tweets(sample_csv):
    source = ReplaySource(sample_csv)
    early = source.search(["debate", "encuesta", "fraude"])
    source.advance(timedelta(days=30))
    late = source.search(["debate", "encuesta", "fraude"])
    assert len(early) < len(late)
    assert all(t.created_at <= source.now for t in late)
