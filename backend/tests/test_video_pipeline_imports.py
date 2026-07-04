"""
Import smoke test for the video agent + vendored Faceless Video Pipeline.

The vendored pipeline uses its own sys.path-hacked bare imports (`import
config as cfg`, `import main`) rather than a proper dotted package, so a
mistake there won't surface as a normal ImportError until something actually
tries to run the pipeline. This test imports every touched module up front —
catching path/naming breakage immediately, before a real generation attempt.

Run:  python -m pytest backend/tests/test_video_pipeline_imports.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_tmp.name}")
os.environ.setdefault("JWT_SECRET", "test-secret")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND_ROOT = Path(__file__).resolve().parents[1]
VENDOR_ROOT = BACKEND_ROOT / "app" / "vendor" / "faceless_pipeline"


def test_video_generator_service_imports():
    from app.services import video_generator  # noqa: F401
    from app.models.generated_video import GeneratedVideo  # noqa: F401
    from app.models.video_channel import VideoChannel  # noqa: F401
    from app.schemas import video as video_schemas  # noqa: F401
    from app.api import videos  # noqa: F401


def test_vendored_pipeline_modules_import():
    """Import every vendored module the same way _run_pipeline_blocking does
    (sys.path insert + bare `import config`/`import main`), so a broken
    self-referential import surfaces here, not mid-generation."""
    if str(VENDOR_ROOT) not in sys.path:
        sys.path.insert(0, str(VENDOR_ROOT))

    import config as cfg  # noqa: F401
    import main as pipeline_main  # noqa: F401
    assert hasattr(pipeline_main, "run_pipeline")

    from steps import (  # noqa: F401
        add_watermark, burn_captions, fetch_clips, generate_audio,
        generate_captions, generate_script, generate_thumbnail,
        merge_clips, mix_audio, render_intro_outro, validate_output,
    )
    assert hasattr(generate_script, "generate_script")
    assert hasattr(generate_script, "_call_llm")


def test_generate_script_uses_openrouter_not_anthropic():
    """Regression guard: confirms the provider swap actually stuck — this
    file was migrated off the Anthropic SDK to a free model via OpenRouter."""
    if str(VENDOR_ROOT) not in sys.path:
        sys.path.insert(0, str(VENDOR_ROOT))
    from steps import generate_script
    import inspect
    source = inspect.getsource(generate_script._call_llm)
    assert "openai" in source
    assert "anthropic" not in source.lower()


def test_config_validates_openrouter_not_anthropic_key():
    if str(VENDOR_ROOT) not in sys.path:
        sys.path.insert(0, str(VENDOR_ROOT))
    import config as cfg
    assert hasattr(cfg, "OPENROUTER_API_KEY")
    assert not hasattr(cfg, "ANTHROPIC_API_KEY")
