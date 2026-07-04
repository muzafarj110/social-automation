"""
Step 4 — Render intro and outro cards using Pillow + FFmpeg.

Pillow draws the text/graphics onto a PNG frame; FFmpeg converts it to a
5-second video with fade-in / fade-out.  No libfreetype required in FFmpeg.

Standalone:
    python steps/render_intro_outro.py --title "5 Money Mistakes" --handle "@MoneyFacts" \
        --color "#00c805" --out-intro temp/intro.mp4 --out-outro temp/outro.mp4
"""
import sys, subprocess, argparse, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config as cfg

DURATION   = 5
FADE_DUR   = 0.4
W, H       = cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT   # 1080 × 1920


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try a handful of system fonts, fall back to PIL default."""
    candidates = []
    if bold:
        candidates += [
            str(ROOT / "assets" / "fonts" / "Inter-900.ttf"),
            str(ROOT / "assets" / "fonts" / "Inter-Bold.ttf"),
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
    else:
        candidates += [
            str(ROOT / "assets" / "fonts" / "Inter-400.ttf"),
            str(ROOT / "assets" / "fonts" / "Inter-Regular.ttf"),
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass

    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _draw_text_centered(
    draw: ImageDraw.Draw,
    text: str,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    max_width: int = W - 120,
    shadow: bool = True,
) -> int:
    """Draw horizontally centered text with optional drop shadow. Returns y after text."""
    # Wrap
    lines = []
    for raw_line in text.split("\n"):
        # rough wrap using font metrics
        words = raw_line.split()
        cur = []
        for word in words:
            test = " ".join(cur + [word])
            w_px = draw.textlength(test, font=font)
            if w_px > max_width and cur:
                lines.append(" ".join(cur))
                cur = [word]
            else:
                cur.append(word)
        if cur:
            lines.append(" ".join(cur))

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        if shadow:
            draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 160))
        draw.text((x, y), line, font=font, fill=fill)
        y += (bbox[3] - bbox[1]) + 14

    return y


def _grid_overlay(img: Image.Image, step: int = 80, alpha: int = 12) -> None:
    """Draw a subtle grid on the image in-place."""
    draw = ImageDraw.Draw(img, "RGBA")
    for x in range(0, W, step):
        draw.line([(x, 0), (x, H)], fill=(255, 255, 255, alpha), width=1)
    for y in range(0, H, step):
        draw.line([(0, y), (W, y)], fill=(255, 255, 255, alpha), width=1)


def _to_video(png_path: Path, out_path: Path, duration: int = DURATION, fade: float = FADE_DUR) -> Path:
    """Convert a static PNG to a video with fade in/out."""
    fade_out_start = duration - fade
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(png_path),
            "-vf", f"fade=t=in:st=0:d={fade},fade=t=out:st={fade_out_start}:d={fade}",
            "-t", str(duration),
            "-r", "30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast",
            str(out_path),
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr[-600:]}")
    return out_path


# ── Public API ────────────────────────────────────────────────────────────────

def render_intro(title: str, handle: str, accent: str, out_path: Path) -> Path:
    """Render a 5-second intro card (Pillow + FFmpeg)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_png = out_path.with_suffix(".png")

    r, g, b = _hex_to_rgb(accent)

    # Base dark background
    img  = Image.new("RGBA", (W, H), (6, 6, 15, 255))
    _grid_overlay(img)
    draw = ImageDraw.Draw(img)

    # Accent gradient bar top
    for i in range(6):
        alpha = int(200 * (1 - i / 6))
        draw.rectangle([0, i, W, i + 1], fill=(r, g, b, alpha))

    # Vertical center reference
    mid_y = H // 2

    # Handle label (small, accented)
    font_handle = _load_font(40)
    handle_bbox = draw.textbbox((0, 0), handle, font=font_handle)
    handle_w = handle_bbox[2] - handle_bbox[0]
    handle_x = (W - handle_w) // 2
    draw.text((handle_x + 2, mid_y - 220 + 2), handle, font=font_handle, fill=(0, 0, 0, 120))
    draw.text((handle_x, mid_y - 220), handle, font=font_handle, fill=(r, g, b, 230))

    # Accent underline beneath handle
    draw.rectangle([W // 2 - 160, mid_y - 165, W // 2 + 160, mid_y - 159],
                   fill=(r, g, b, 200))

    # Title text
    font_title = _load_font(76, bold=True)
    _draw_text_centered(draw, title, mid_y - 130, font_title, (255, 255, 255, 255))

    # Small tagline
    font_tag = _load_font(30)
    tag = "Watch till the end ↓"
    tag_bbox = draw.textbbox((0, 0), tag, font=font_tag)
    tag_x = (W - (tag_bbox[2] - tag_bbox[0])) // 2
    draw.text((tag_x, mid_y + 120), tag, font=font_tag, fill=(255, 255, 255, 100))

    # Bottom accent line
    draw.rectangle([0, H - 6, W, H], fill=(r, g, b, 160))

    # Save PNG then convert to video
    img.save(str(tmp_png), "PNG")
    _to_video(tmp_png, out_path)
    tmp_png.unlink(missing_ok=True)

    print(f"  ✓ Intro card: {out_path.name}")
    return out_path


def render_outro(handle: str, accent: str, out_path: Path) -> Path:
    """Render a 5-second outro card (Pillow + FFmpeg)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_png = out_path.with_suffix(".png")

    r, g, b = _hex_to_rgb(accent)

    img  = Image.new("RGBA", (W, H), (6, 6, 15, 255))
    _grid_overlay(img)
    draw = ImageDraw.Draw(img)

    # Top + bottom accent bars
    draw.rectangle([0, 0, W, 6], fill=(r, g, b, 180))
    draw.rectangle([0, H - 6, W, H], fill=(r, g, b, 180))

    mid_y = H // 2

    font_big = _load_font(80, bold=True)
    font_mid = _load_font(44)
    font_sm  = _load_font(34)

    # Main CTA
    _draw_text_centered(draw, "Subscribe", mid_y - 200, font_big, (255, 255, 255, 255))
    _draw_text_centered(draw, "for more!", mid_y - 100, font_big, (r, g, b, 255))

    # Accent rule
    draw.rectangle([W // 2 - 180, mid_y + 10, W // 2 + 180, mid_y + 16],
                   fill=(r, g, b, 200))

    # Handle
    _draw_text_centered(draw, handle, mid_y + 40, font_mid, (255, 255, 255, 230))

    # Notification CTA
    _draw_text_centered(draw, "Turn on notifications", mid_y + 120, font_sm,
                        (255, 255, 255, 140), shadow=False)

    img.save(str(tmp_png), "PNG")
    _to_video(tmp_png, out_path)
    tmp_png.unlink(missing_ok=True)

    print(f"  ✓ Outro card: {out_path.name}")
    return out_path


def _draw_hook_overlay(img: Image.Image, hook_text: str, accent: tuple, font_hook, font_sub) -> None:
    """Draw hook text overlay onto a single frame (in-place)."""
    r, g, b = accent
    draw = ImageDraw.Draw(img, "RGBA")

    # Dark gradient overlay so text pops over any background
    for i in range(H):
        darkness = int(170 * (1 - abs(i - H // 2) / (H // 2)) + 60)
        draw.rectangle([0, i, W, i + 1], fill=(0, 0, 0, min(darkness, 200)))

    # Accent bar top
    for i in range(8):
        a = int(220 * (1 - i / 8))
        draw.rectangle([0, i, W, i + 1], fill=(r, g, b, a))

    # Hook text — large, bold, centered
    _draw_text_centered(draw, hook_text.upper(), H // 2 - 160, font_hook,
                        (255, 255, 255, 255), max_width=W - 80)

    # Accent underline
    draw.rectangle([W // 2 - 120, H // 2 + 60, W // 2 + 120, H // 2 + 68],
                   fill=(r, g, b, 220))

    # "Watch this 👇" sub-label
    sub = "Watch this  👇"
    sub_bbox = draw.textbbox((0, 0), sub, font=font_sub)
    sub_x = (W - (sub_bbox[2] - sub_bbox[0])) // 2
    draw.text((sub_x, H // 2 + 90), sub, font=font_sub, fill=(r, g, b, 220))


def render_hook_screen(
    hook_text: str,
    accent: str,
    out_path: Path,
    duration: int = 3,
    bg_clip: Path | None = None,
) -> Path:
    """
    Render a 3-second full-screen hook card.

    If bg_clip is provided, uses it as a dynamic background (with dark overlay +
    Pillow text burned frame-by-frame). Otherwise falls back to a plain dark card.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r, g, b = _hex_to_rgb(accent)
    accent_rgb = (r, g, b)

    font_size = min(120, max(80, int(900 / max(len(hook_text), 1) * 6)))
    font_hook = _load_font(font_size, bold=True)
    font_sub  = _load_font(36)

    if bg_clip and bg_clip.exists():
        # ── Video background: read frames, overlay text, write ────────────────
        fps        = 30.0
        frame_bytes = W * H * 3

        reader = subprocess.Popen(
            [
                "ffmpeg", "-i", str(bg_clip),
                "-t", str(duration),
                "-vf", f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
                       f"crop={W*2}:{H*2},scale={W}:{H},fps={fps}",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )

        tmp_video = out_path.with_suffix(".tmp.mp4")
        writer = subprocess.Popen(
            [
                "ffmpeg", "-y",
                "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{W}x{H}", "-r", str(fps),
                "-i", "pipe:0",
                "-vf", f"fade=t=in:st=0:d=0.15,fade=t=out:st={duration-0.15}:d=0.15",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-pix_fmt", "yuv420p",
                str(tmp_video),
            ],
            stdin=subprocess.PIPE, stderr=subprocess.DEVNULL
        )

        frame_num = 0
        try:
            while True:
                raw = reader.stdout.read(frame_bytes)
                if len(raw) < frame_bytes:
                    break
                img = Image.frombytes("RGB", (W, H), raw).convert("RGBA")
                _draw_hook_overlay(img, hook_text, accent_rgb, font_hook, font_sub)
                writer.stdin.write(img.convert("RGB").tobytes())
                frame_num += 1
        except BrokenPipeError:
            pass
        finally:
            writer.stdin.close()
            reader.stdout.close()

        reader.wait()
        writer.wait()

        if writer.returncode != 0 or frame_num == 0:
            tmp_video.unlink(missing_ok=True)
            print("  ⚠ Hook bg encode failed — falling back to plain card")
            return render_hook_screen(hook_text, accent, out_path, duration, bg_clip=None)

        import shutil
        shutil.move(str(tmp_video), str(out_path))
        print(f"  ✓ Hook screen (Pexels bg): {out_path.name}  (\"{hook_text}\")")
        return out_path

    # ── Fallback: plain dark card (original behaviour) ────────────────────────
    tmp_png = out_path.with_suffix(".png")
    img  = Image.new("RGBA", (W, H), (4, 4, 10, 255))
    _draw_hook_overlay(img, hook_text, accent_rgb, font_hook, font_sub)
    img.save(str(tmp_png), "PNG")
    _to_video(tmp_png, out_path, duration=duration, fade=0.15)
    tmp_png.unlink(missing_ok=True)

    print(f"  ✓ Hook screen: {out_path.name}  (\"{hook_text}\")")
    return out_path


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--title",      default="5 Money Mistakes in Your 20s")
    parser.add_argument("--handle",     default="@MoneyFacts")
    parser.add_argument("--color",      default="#00c805")
    parser.add_argument("--out-intro",  default="/tmp/intro.mp4")
    parser.add_argument("--out-outro",  default="/tmp/outro.mp4")
    args = parser.parse_args()

    render_intro(args.title, args.handle, args.color, Path(args.out_intro))
    render_outro(args.handle, args.color, Path(args.out_outro))
    print(f"\n  Done: {args.out_intro}  {args.out_outro}")
