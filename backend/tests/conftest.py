"""
Test-wide configuration.

The suite must be deterministic and OFFLINE — it must never call the real Zernio
or Hub APIs. White-label mode is switched on by an app-level ZERNIO_API_KEY, and
in that mode `ensure_profile` would hit the live Zernio API (creating profiles).
So we blank ZERNIO_API_KEY for the whole suite, which runs every test in legacy
(per-user-key) mode with mocked clients. The dedicated white-label test forces
white-label mode itself via monkeypatch, so it's unaffected.

This runs before any test module imports the app, so app.core.config.settings
loads with the empty value (env vars override the .env file in pydantic-settings).
"""

import os

os.environ["ZERNIO_API_KEY"] = ""
