"""
Supported social platforms (via Zernio) — the single source of truth.

The Zernio `/posts` API takes a `platforms: [{platform, accountId}]` array, so
the app is platform-agnostic: we just need the right `platform` string and to
respect each platform's content norms (length, hashtags, media).

`char_limit` is the hard cap we trim to before sending; `supports_hashtags`
drives whether we append hashtags to the body; `media_required` flags platforms
that won't accept a text-only post (we surface this in the UI / skip in auto).
"""

from __future__ import annotations

# API value -> metadata. API values match Zernio exactly (docs.zernio.com).
PLATFORMS: dict[str, dict] = {
    "twitter":        {"label": "X (Twitter)",     "char_limit": 280,   "supports_hashtags": True,  "media_required": False},
    "instagram":      {"label": "Instagram",       "char_limit": 2200,  "supports_hashtags": True,  "media_required": True},
    "facebook":       {"label": "Facebook",        "char_limit": 63206, "supports_hashtags": True,  "media_required": False},
    "linkedin":       {"label": "LinkedIn",        "char_limit": 3000,  "supports_hashtags": True,  "media_required": False},
    "tiktok":         {"label": "TikTok",          "char_limit": 2200,  "supports_hashtags": True,  "media_required": True},
    "youtube":        {"label": "YouTube",         "char_limit": 5000,  "supports_hashtags": True,  "media_required": True},
    "pinterest":      {"label": "Pinterest",       "char_limit": 500,   "supports_hashtags": True,  "media_required": True},
    "reddit":         {"label": "Reddit",          "char_limit": 40000, "supports_hashtags": False, "media_required": False},
    "bluesky":        {"label": "Bluesky",         "char_limit": 300,   "supports_hashtags": True,  "media_required": False},
    "threads":        {"label": "Threads",         "char_limit": 500,   "supports_hashtags": True,  "media_required": False},
    "googlebusiness": {"label": "Google Business", "char_limit": 1500,  "supports_hashtags": False, "media_required": False},
    "telegram":       {"label": "Telegram",        "char_limit": 4096,  "supports_hashtags": True,  "media_required": False},
    "snapchat":       {"label": "Snapchat",        "char_limit": 250,   "supports_hashtags": False, "media_required": True},
    "whatsapp":       {"label": "WhatsApp",        "char_limit": 4096,  "supports_hashtags": False, "media_required": False},
    "discord":        {"label": "Discord",         "char_limit": 2000,  "supports_hashtags": True,  "media_required": False},
}

DEFAULT_PLATFORM = "linkedin"
PLATFORM_KEYS = list(PLATFORMS.keys())
# Regex alternation for pydantic patterns: ^(twitter|instagram|...)$
PLATFORM_PATTERN = "^(" + "|".join(PLATFORM_KEYS) + ")$"


def is_valid(platform: str) -> bool:
    return platform in PLATFORMS


def meta(platform: str) -> dict:
    return PLATFORMS.get(platform, PLATFORMS[DEFAULT_PLATFORM])


def label(platform: str) -> str:
    return meta(platform)["label"]


def char_limit(platform: str) -> int:
    return meta(platform)["char_limit"]


def supports_hashtags(platform: str) -> bool:
    return meta(platform)["supports_hashtags"]


def normalize(platform: str | None) -> str:
    """Lowercase + validate, falling back to the default platform."""
    p = (platform or "").strip().lower()
    return p if p in PLATFORMS else DEFAULT_PLATFORM
