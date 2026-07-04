"""
Step 6 — Mix voiceover + background music into the merged video.

Picks a random MP3 from assets/music/<style>/ (looped to video length).
Voiceover at 100%, music at MUSIC_VOLUME (default 15%).

Standalone:
    python steps/mix_audio.py --video temp/merged.mp4 --voice temp/voiceover.mp3 \
        --music-style calm --out temp/with_audio.mp4
"""
import sys, random, subprocess, argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config as cfg


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg audio mix failed:\n{result.stderr[-600:]}")


def _pick_music(music_dir: Path, style: str) -> Path | None:
    """Pick a random MP3 from assets/music/<style>/."""
    style_dir = music_dir / style
    mp3s = list(style_dir.glob("*.mp3"))
    if not mp3s:
        # Fall back to any music folder
        mp3s = list(music_dir.rglob("*.mp3"))
    if not mp3s:
        return None
    chosen = random.choice(mp3s)
    print(f"  [Audio] Background music: {chosen.name}")
    return chosen


def mix_audio(
    video_path: Path,
    voiceover_path: Path,
    out_path: Path,
    music_dir: Path,
    music_style: str = "calm",
    music_volume: float | None = None,
) -> Path:
    """
    Replace video audio with: voiceover (100%) + bg music (music_volume %).
    Music is looped if shorter than the video.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vol = music_volume if music_volume is not None else cfg.MUSIC_VOLUME
    music = _pick_music(music_dir, music_style)

    if music:
        # voiceover + looped background music, mixed
        filter_complex = (
            f"[1:a]volume=1.0[voice];"
            f"[2:a]volume={vol},aloop=loop=-1:size=2e+09[bg];"
            f"[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[audio]"
        )
        _run_ffmpeg([
            "-i", str(video_path),
            "-i", str(voiceover_path),
            "-i", str(music),
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[audio]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(out_path)
        ])
    else:
        # No music found — just attach voiceover
        print("  ⚠ No background music found — using voiceover only")
        _run_ffmpeg([
            "-i", str(video_path),
            "-i", str(voiceover_path),
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(out_path)
        ])

    print(f"  ✓ Audio mixed: {out_path.name}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",       required=True)
    parser.add_argument("--voice",       required=True)
    parser.add_argument("--music-style", default="calm")
    parser.add_argument("--out",         required=True)
    args = parser.parse_args()

    mix_audio(
        Path(args.video),
        Path(args.voice),
        Path(args.out),
        ROOT / "assets" / "music",
        music_style=args.music_style,
    )
