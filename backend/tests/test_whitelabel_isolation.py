"""
White-label isolation: with one app-level Zernio key, a customer must ONLY ever
see accounts under their own Zernio Profile — even if the upstream API returns
more. This proves the fail-closed filter in services/channels.list_customer_accounts.

Run:  python -m pytest backend/tests/test_whitelabel_isolation.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("JWT_SECRET", "test-secret-please-change")
os.environ.setdefault("HUB_BASE_URL", "https://hub.example.com")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from app.services import channels  # noqa: E402
from app.models.user import User  # noqa: E402


class _FakeDB:
    async def commit(self):  # ensure_profile commits the new profile id
        return None


class _FakeZ:
    """Deliberately OVER-RETURNS accounts from two different profiles."""
    def __init__(self, *a, **k): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *e): return False
    async def create_profile(self, *, name, description=""):
        return {"_id": "profA"}
    async def list_accounts(self, *, profile_id=None):
        return {"accounts": [
            {"_id": "accA", "platform": "linkedin", "profileId": {"_id": "profA"}},
            # Another customer's account — must be filtered out, fail-closed:
            {"_id": "accB", "platform": "twitter", "profileId": {"_id": "profB"}},
        ]}


@pytest.mark.asyncio
async def test_customer_only_sees_own_profile_accounts(monkeypatch):
    # Force white-label mode + the app key, regardless of env/singleton state.
    monkeypatch.setattr(channels.settings, "zernio_api_key", "appkey-not-paste")
    monkeypatch.setattr(channels, "is_white_label", lambda: True)
    monkeypatch.setattr(channels, "resolve_zernio_key", lambda u: "appkey-not-paste")
    monkeypatch.setattr(channels, "ZernioClient", _FakeZ)

    u = User()
    u.id = 1
    u.email = "a@b.com"
    u.zernio_profile_id = None

    accts = await channels.list_customer_accounts(u, _FakeDB())
    ids = {a["_id"] for a in accts}

    assert u.zernio_profile_id == "profA"     # profile created + stored
    assert ids == {"accA"}                     # ONLY this customer's profile
    assert "accB" not in ids                   # the other customer's account is dropped
