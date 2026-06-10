"""
Live smoke test against the real AI Models Hub.

Usage:
    export HUB_BASE_URL="https://your-hub.up.railway.app"
    export HUB_API_KEY="your-real-key"
    python backend/scripts/smoke_hub.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.hub_client import HubClient, HubError  # noqa: E402


def load_dotenv() -> None:
    """Load backend/.env into os.environ (no external dependency)."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


async def main() -> int:
    load_dotenv()
    base = os.environ.get("HUB_BASE_URL")
    key = os.environ.get("HUB_API_KEY")
    if not base or not key or key.startswith("paste-"):
        print("Set HUB_API_KEY in backend/.env (HUB_BASE_URL is already filled).")
        return 2

    async with HubClient(base, key) as hub:
        try:
            data = await hub.generate_text_post(
                topic="I almost quit my startup after 6 months with zero revenue",
                post_type="Personal Story + Lesson",
                audience="early-stage founders",
                tone="professional but human",
                include_cta="question to comments",
            )
        except HubError as exc:
            print(f"Hub call failed ({exc.status_code}): {exc.message}")
            return 1

    print("OK — Hub responded. log_id:", data.get("_log_id"))
    print("character_count:", data.get("character_count"))
    print("hook:", data.get("hook", "")[:80])
    print("\nfull_post (first 300 chars):\n", json.dumps(data.get("full_post", ""))[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
