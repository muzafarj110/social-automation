"""
Near-duplicate topic detection for the content strategist's weekly plan.

Run:  python -m pytest backend/tests/test_team_dedup.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_tmp.name}")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("HUB_BASE_URL", "https://hub.example.com")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.team import _similar, _topics_from_strategy  # noqa: E402


def test_similar_catches_reworded_duplicate():
    assert _similar(
        "5 AI tools for productivity", "5 AI tools to boost productivity"
    )


def test_similar_catches_the_audit_reported_duplicate():
    # The exact pair a live customer audit found in one "Plan a week" batch.
    assert _similar(
        "Foundations of Content Strategy",
        "What is Content Strategy? A Beginner's Guide",
    )


def test_similar_rejects_unrelated_topics():
    assert not _similar(
        "5 AI tools for productivity", "How to hire your first salesperson"
    )


def test_similar_rejects_same_template_different_subject():
    # Shared generic opener ("What is X") must not be enough on its own.
    assert not _similar("What is Docker", "What is Kubernetes")


def test_topics_from_strategy_dedups_near_duplicates():
    data = {
        "content_pillars": [
            "Foundations of Content Strategy",
            "What is Content Strategy? A Beginner's Guide",
            "5 AI tools for productivity",
        ]
    }
    topics = _topics_from_strategy(data, count=3)
    assert topics == ["Foundations of Content Strategy", "5 AI tools for productivity"]
