"""
Step 9 — Overlay logo watermark on video.

Positions logo bottom-right with configurable opacity and padding.
Logo path: assets/logo.png (all channels share one logo).

Standalone:
    python steps/add_watermark.py --video temp/captioned.mp4 --out temp/watermarked.mp4
"""
import sys, subprocess, argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config as cfg


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg watermark failed:\n{result.stderr[-600:]}")


def add_watermark(
    video_path: Path,
    logo_path: Path,
    out_path: Path,
    opacity: float | None = None,
    logo_width: int = 140,
    padding: int = 20,
) -> Path:
    """
    Overlay logo bottom-right corner at given opacity.
    logo_width controls the size; aspect ratio is preserved.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not logo_path.exists():
        print(f"  ⚠ Logo not found at {logo_path} — skipping watermark")
        import shutil
        shutil.copy(video_path, out_path)
        return out_path

    op = opacity if opacity is not None else cfg.WATERMARK_OPACITY

    # Scale logo, apply opacity, overlay bottom-right
    filter_complex = (
        f"[1:v]scale={logo_width}:-1,"
        f"format=rgba,"
        f"colorchannelmixer=aa={op}"
        f"[logo];"
        f"[0:v][logo]overlay=W-w-{padding}:H-h-{padding}"
    )

    _run_ffmpeg([
        "-i", str(video_path),
        "-i", str(logo_path),
        "-filter_complex", filter_complex,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        str(out_path)
    ])

    print(f"  ✓ Watermark added: {out_path.name}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out",   required=True)
    parser.add_argument("--logo",  default=str(ROOT / "assets" / "logo.png"))
    args = parser.parse_args()

    add_watermark(Path(args.video), Path(args.logo), Path(args.out))
