"""
Multi-platform unit tests — content adaptation + Zernio platform entries.

No network: we test pure functions (platform registry, publisher content
composition) and that the Zernio client builds the right `platforms[]` payload.

Run:  python -m pytest backend/tests/test_multiplatform.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("JWT_SECRET", "test-secret-please-change")
os.environ.setdefault("HUB_BASE_URL", "https://hub.example.com")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import platforms as plat  # noqa: E402
from app.services import publisher  # noqa: E402
from app.clients.zernio_client import ZernioClient  # noqa: E402
from app.models.post import Post  # noqa: E402


def _post(body: str, hashtags=None) -> Post:
    p = Post()
    p.id = 1
    p.body = body
    p.hashtags = hashtags
    p.first_comment = None
    p.media = None
    return p


def test_all_15_platforms_present():
    assert len(plat.PLATFORMS) == 15
    for key in ["twitter", "instagram", "linkedin", "tiktok", "youtube", "bluesky",
                "threads", "reddit", "pinterest", "facebook", "snapchat",
                "whatsapp", "discord", "telegram", "googlebusiness"]:
        assert plat.is_valid(key), key


def test_normalize_falls_back_to_linkedin():
    assert plat.normalize("Twitter") == "twitter"
    assert plat.normalize("not-a-platform") == "linkedin"
    assert plat.normalize(None) == "linkedin"


def test_twitter_content_is_trimmed_to_limit():
    long_body = "x" * 500
    out = publisher._compose_content(_post(long_body), "twitter")
    assert len(out) <= plat.char_limit("twitter")  # 280
    assert out.endswith("…")


def test_hashtags_appended_only_where_supported():
    p = _post("Hello world", hashtags=["growth", "ai"])
    li = publisher._compose_content(p, "linkedin")
    assert "#growth" in li and "#ai" in li
    # Reddit doesn't use hashtags — they should be dropped.
    rd = publisher._compose_content(p, "reddit")
    assert "#growth" not in rd and "#ai" not in rd


def test_first_comment_is_linkedin_only():
    p = _post("Body")
    p.first_comment = "First!"
    assert publisher._psd_for(p, "linkedin") == {"firstComment": "First!"}
    assert publisher._psd_for(p, "twitter") is None


def test_zernio_platform_entry_shape():
    entry = ZernioClient._platform_entry("twitter", "acc_123")
    assert entry == {"platform": "twitter", "accountId": "acc_123"}
    entry2 = ZernioClient._platform_entry(
        "linkedin", "acc_x", platform_specific_data={"firstComment": "Hi"})
    assert entry2["platformSpecificData"] == {"firstComment": "Hi"}
