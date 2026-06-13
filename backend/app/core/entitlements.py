"""
Feature entitlements — what each plan unlocks, with per-user admin overrides.

Effective features = plan defaults, then any admin override merged on top.
The frontend reads these to show/lock features; sensitive endpoints can also
guard with `require_feature`.
"""

from __future__ import annotations

from app.core.config import settings
from app.models.user import User


def is_admin(user: User) -> bool:
    return bool(settings.admin_email) and (user.email or "").lower() == settings.admin_email.lower()

# All gateable features (keys used by both backend and frontend).
FEATURES = [
    "generate", "qa", "strategy", "autopilot", "inbox",
    "profile_studio", "analytics", "infographics",
    "learn_from_analytics", "multi_account",
]

# Plan → features turned on. Anything not listed defaults to off.
# Free includes a limited taste of the headline Autopilot feature (capped below).
PLAN_FEATURES: dict[str, dict[str, bool]] = {
    "free": {"generate": True, "qa": True, "analytics": True, "autopilot": True},
    "pro": {f: True for f in FEATURES},
    "business": {f: True for f in FEATURES},
}

# Numeric caps per plan. None = unlimited. Admin is always unlimited.
PLAN_LIMITS: dict[str, dict[str, int | None]] = {
    "free": {"max_campaigns": 1, "max_posts_per_week": 3},
    "pro": {"max_campaigns": None, "max_posts_per_week": None},
    "business": {"max_campaigns": None, "max_posts_per_week": None},
}


def plan_limit(user: User, key: str) -> int | None:
    """The numeric limit for a plan feature, or None for unlimited."""
    if is_admin(user):
        return None
    return PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"]).get(key)


def effective_entitlements(user: User) -> dict[str, bool]:
    """Resolve the user's enabled features: plan defaults + admin override."""
    if is_admin(user):
        return {f: True for f in FEATURES}
    out = {f: False for f in FEATURES}
    out.update(PLAN_FEATURES.get(user.plan, PLAN_FEATURES["free"]))
    override = getattr(user, "entitlements_override", None)
    if isinstance(override, dict):
        for k, v in override.items():
            if k in out:
                out[k] = bool(v)
    return out


def has_feature(user: User, feature: str) -> bool:
    return effective_entitlements(user).get(feature, False)
