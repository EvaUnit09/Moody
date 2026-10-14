"""Rerun check for the old Locust ` v{n}` suffix vs should_expand.

Misses used to append a word. That flipped some two-word moods off
query expansion. The locustfile now keeps the typed mood and busts the
cache with a sentinel exclude id. This file is the table in
docs/STRESS_TEST_MEASUREMENT.md, as a test.
"""

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from app.services.query_intent import should_expand

QUERIES_PATH = Path(__file__).resolve().parents[1] / "loadtest" / "mood_queries.json"


@pytest.fixture(scope="module")
def mood_queries() -> list[str]:
    queries = json.loads(QUERIES_PATH.read_text())
    assert isinstance(queries, list)
    return queries


def test_mood_pool_size(mood_queries: list[str]) -> None:
    assert len(mood_queries) == 100


def test_old_v_suffix_flips_three_two_word_moods(mood_queries: list[str]) -> None:
    would_expand = [q for q in mood_queries if should_expand(q)]
    flipped = [q for q in would_expand if not should_expand(f"{q} v0")]
    still_expand = [q for q in would_expand if should_expand(f"{q} v0")]

    assert would_expand == [
        "uplifting",
        "thriller",
        "feel-good",
        "heist comedy",
        "office satire",
    ]
    assert flipped == ["feel-good", "heist comedy", "office satire"]
    assert still_expand == ["uplifting", "thriller"]
