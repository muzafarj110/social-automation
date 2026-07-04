"""
Step 10 — Generate thumbnail from video frame + title overlay.

Extracts a frame at 3 seconds, applies a gradient overlay,
then renders the title in large bold text centered on the image.

Standalone:
    python steps/generate_thumbnail.py --video temp/watermarked.mp4 \
        --title "5 Money Mistakes" --color "#00c805" --out output/finance/thumb.jpg
"""
import sys, subprocess, argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config as cfg


def _extract_frame(video_path: Path, out_path: Path, timestamp: float = 3.0) -> Path:
    """Extract a single frame from video at given timestamp."""
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path),
         "-ss", str(timestamp), "-vframes", "1",
         "-q:v", "2", str(out_path)],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not out_path.exists():
        raise RuntimeError(f"Frame extract failed: {result.stderr[-400:]}")
    return out_path


def _wrap_text(text: str, max_chars: int = 18) -> list[str]:
    """Wrap text into lines of max_chars."""
    words, lines, line = text.split(), [], []
    for word in words:
        if len(" ".join(line + [word])) > max_chars:
            if line:
                lines.append(" ".join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        lines.append(" ".join(line))
    return lines


def generate_thumbnail(
    video_path: Path,
    title: str,
    out_path: Path,
    accent: str = "#4fc3f7",
    fonts_dir: Path | None = None,
    timestamp: float = 3.0,
) -> Path:
    """
    Extract frame → gradient overlay → title text → save JPG thumbnail.
    """
    from PIL import Image, ImageDraw, ImageFont
    import textwrap

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Extract raw frame
    raw_frame = out_path.parent / "_thumb_raw.jpg"
    _extract_frame(video_path, raw_frame, timestamp)

    img = Image.open(raw_frame).convert("RGB")
    w, h = img.size

    draw = ImageDraw.Draw(img, "RGBA")

    # Dark gradient overlay (bottom 60% of frame)
    for y in range(h):
        pct = max(0, (y - h * 0.3) / (h * 0.7))
        alpha = int(min(200, pct * 220))
        draw.line([(0, y), (w, y)], fill=(6, 6, 15, alpha))

    # Accent bar
    bar_y = int(h * 0.62)
    bar_w = int(w * 0.55)
    draw.rectangle([80, bar_y, 80 + bar_w, bar_y + 8],
                   fill=_hex_to_rgb(accent) + (220,))

    # Try to load a font, fall back to default
    font_title = None
    font_sub   = None
    if fonts_dir and fonts_dir.exists():
        for fname in ["Inter-900.ttf", "Inter-Bold.ttf", "Arial Bold.ttf", "arial.ttf"]:
            fp = fonts_dir / fname
            if fp.exists():
                try:
                    font_title = ImageFont.truetype(str(fp), size=int(h * 0.08))
                    font_sub   = ImageFont.truetype(str(fp), size=int(h * 0.04))
                    break
                except Exception:
                    pass
    if font_title is None:
        try:
            font_title = ImageFont.load_default(size=int(h * 0.08))
            font_sub   = ImageFont.load_default(size=int(h * 0.04))
        except Exception:
            font_title = ImageFont.load_default()
            font_sub   = font_title

    # Title text
    lines = _wrap_text(title, max_chars=16)
    text_y = int(h * 0.65)
    for line in lines:
        # Shadow
        draw.text((84, text_y + 3), line, font=font_title, fill=(0, 0, 0, 180))
        # White text
        draw.text((80, text_y), line, font=font_title, fill=(255, 255, 255, 255))
        text_y += int(h * 0.1)

    # Save
    img.save(str(out_path), "JPEG", quality=92)
    raw_frame.unlink(missing_ok=True)

    print(f"  ✓ Thumbnail: {out_path.name} ({w}x{h})")
    return out_path


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--color", default="#4fc3f7")
    parser.add_argument("--out",   required=True)
    args = parser.parse_args()

    generate_thumbnail(
        Path(args.video),
        args.title,
        Path(args.out),
        accent=args.color,
        fonts_dir=ROOT / "assets" / "fonts",
    )
