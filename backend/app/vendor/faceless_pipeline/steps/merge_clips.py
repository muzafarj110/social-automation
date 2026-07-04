"""
Step 5 — Merge intro + clips + outro into a single video.

Each clip is:
  - Trimmed to clip_duration seconds
  - Scaled and cropped to OUTPUT_RESOLUTION (portrait 1080x1920)
  - Concatenated in order

Standalone:
    python steps/merge_clips.py --intro temp/intro.mp4 --clips temp/clips/ \
        --outro temp/outro.mp4 --duration 8 --out temp/merged.mp4
"""
import sys, subprocess, tempfile, argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config as cfg


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg merge failed:\n{result.stderr[-600:]}")


def _normalize_clip(src: Path, dest: Path, duration: int) -> None:
    """Trim + scale/crop + Ken Burns zoom on a clip to portrait format."""
    w, h = cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT
    frames = duration * 30  # at 30fps
    # Scale to fill portrait, crop center, then apply slow zoom-in (Ken Burns)
    # zoompan: z goes from 1.0 → 1.12 over the clip duration for subtle motion
    vf = (
        f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
        f"crop={w*2}:{h*2},"
        f"zoompan=z='min(zoom+0.0005,1.12)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={w}x{h}:fps=30,"
        f"setsar=1"
    )
    _run_ffmpeg([
        "-i", str(src),
        "-t", str(duration),
        "-vf", vf,
        "-r", "30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-an",
        "-preset", "fast",
        str(dest)
    ])


def merge_clips(
    clips: list[Path],
    intro: Path,
    outro: Path,
    out_path: Path,
    clip_duration: int = 8,
    hook: Path | None = None,
) -> Path:
    """
    Normalize all clips to portrait format and concatenate:
      hook(3s) + intro(5s) + clips[0..n] + outro(5s) → out_path
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    norm_dir = out_path.parent / "normalized"
    norm_dir.mkdir(exist_ok=True)

    print(f"  [Merge] Normalizing {len(clips)} clips to {cfg.OUTPUT_RESOLUTION}...")

    # Normalize each B-roll clip (with Ken Burns zoom)
    normalized: list[Path] = []
    for i, clip in enumerate(clips):
        dest = norm_dir / f"norm_{i:03d}.mp4"
        if not dest.exists():
            _normalize_clip(clip, dest, clip_duration)
        normalized.append(dest)
        print(f"    clip {i+1}/{len(clips)} ✓")

    # Normalize intro + outro + optional hook to ensure consistent format
    intro_norm = norm_dir / "intro_norm.mp4"
    outro_norm = norm_dir / "outro_norm.mp4"

    cards = [(intro, intro_norm), (outro, outro_norm)]
    if hook and hook.exists():
        hook_norm = norm_dir / "hook_norm.mp4"
        cards.append((hook, hook_norm))

    for src, dst in cards:
        w, h = cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
        _run_ffmpeg([
            "-i", str(src),
            "-vf", vf, "-r", "30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast", str(dst)
        ])

    # Build concat list: hook → intro → clips → outro
    leaders = []
    if hook and hook.exists():
        leaders.append(norm_dir / "hook_norm.mp4")
    leaders.append(intro_norm)
    all_clips = leaders + normalized + [outro_norm]
    concat_list = out_path.parent / "concat_list.txt"
    with open(concat_list, "w") as f:
        for p in all_clips:
            f.write(f"file '{p.resolve()}'\n")

    print(f"  [Merge] Concatenating {len(all_clips)} segments...")
    _run_ffmpeg([
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "fast",
        "-r", "30", "-vsync", "cfr",      # enforce constant 30fps — fixes caption sync
        "-pix_fmt", "yuv420p",
        str(out_path)
    ])

    duration_secs = len(clips) * clip_duration + 10  # +10 for intro+outro
    print(f"  ✓ Merged: {out_path.name}  (~{duration_secs}s)")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--intro",    required=True)
    parser.add_argument("--clips",    required=True, help="Directory of clip files")
    parser.add_argument("--outro",    required=True)
    parser.add_argument("--duration", type=int, default=8)
    parser.add_argument("--out",      required=True)
    args = parser.parse_args()

    clips = sorted(Path(args.clips).glob("*.mp4"))
    merge_clips(clips, Path(args.intro), Path(args.outro), Path(args.out), args.duration)
