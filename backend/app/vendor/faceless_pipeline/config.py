"""
Central config — loads .env + channel YAML, exposes typed settings.
All paths are relative to the project root so the folder is portable.
"""
import os, yaml, platform
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


def _detect_whisper_backend() -> str:
    """Auto-select mlx-whisper on Apple Silicon, openai-whisper elsewhere."""
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return "mlx-whisper"
    return "openai-whisper"


# ── Global settings (from .env) ───────────────────────────────────────────────

PEXELS_API_KEY    = os.getenv("PEXELS_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

TTS_ENGINE = os.getenv("TTS_ENGINE", "edge-tts")
TTS_VOICE  = os.getenv("TTS_VOICE", "en-US-GuyNeural")

WHISPER_BACKEND = os.getenv("WHISPER_BACKEND", _detect_whisper_backend())
WHISPER_MODEL   = os.getenv("WHISPER_MODEL", "base")

OUTPUT_RESOLUTION = os.getenv("OUTPUT_RESOLUTION", "1080x1920")
MUSIC_VOLUME      = float(os.getenv("MUSIC_VOLUME", "0.15"))
WATERMARK_OPACITY = float(os.getenv("WATERMARK_OPACITY", "0.7"))

_w, _h       = OUTPUT_RESOLUTION.split("x")
VIDEO_WIDTH  = int(_w)
VIDEO_HEIGHT = int(_h)


# ── Channel config loader ─────────────────────────────────────────────────────

def load_channel(name: str) -> dict:
    """Load channels/<name>.yaml and return the config dict."""
    path = ROOT / "channels" / f"{name}.yaml"
    if not path.exists():
        available = [p.stem for p in (ROOT / "channels").glob("*.yaml")]
        raise FileNotFoundError(
            f"Channel '{name}' not found. Available: {available}"
        )
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg["_name"] = name
    return cfg


# ── Path helpers ──────────────────────────────────────────────────────────────

def get_paths(channel_name: str, run_id: str) -> dict:
    """Return all file paths for a pipeline run."""
    temp = ROOT / "temp" / run_id
    out  = ROOT / "output" / channel_name

    temp.mkdir(parents=True, exist_ok=True)
    (temp / "clips").mkdir(exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    return {
        "root":           ROOT,
        "temp":           temp,
        "output":         out,
        "clips_dir":      temp / "clips",
        "voiceover_s":    temp / "voiceover_short.mp3",
        "voiceover_l":    temp / "voiceover_long.mp3",
        "intro":          temp / "intro.mp4",
        "outro":          temp / "outro.mp4",
        "merged_s":       temp / "merged_short.mp4",
        "merged_l":       temp / "merged_long.mp4",
        "mixed_s":        temp / "mixed_short.mp4",
        "mixed_l":        temp / "mixed_long.mp4",
        "captions_s":     temp / "captions_short.srt",
        "captions_l":     temp / "captions_long.srt",
        "captioned_s":    temp / "captioned_short.mp4",
        "captioned_l":    temp / "captioned_long.mp4",
        "watermarked_s":  temp / "watermarked_short.mp4",
        "watermarked_l":  temp / "watermarked_long.mp4",
        "logo":           ROOT / "assets" / "logo.png",
        "fonts_dir":      ROOT / "assets" / "fonts",
        "music_dir":      ROOT / "assets" / "music",
        "thumbnail":      temp / "thumbnail.jpg",
    }


# ── Validation ────────────────────────────────────────────────────────────────

def validate():
    """Fail fast if required config is missing."""
    errors = []
    if not PEXELS_API_KEY:
        errors.append("PEXELS_API_KEY not set in .env")
    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY not set in .env")
    if not (ROOT / "assets" / "logo.png").exists():
        errors.append("assets/logo.png not found — add your logo file")
    if errors:
        raise EnvironmentError("Config errors:\n" + "\n".join(f"  • {e}" for e in errors))
