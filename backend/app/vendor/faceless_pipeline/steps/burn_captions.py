"""
Step 8 — Burn SRT captions into video using Pillow + FFmpeg raw frame pipes.

No libass / libfreetype needed in FFmpeg. Pillow renders text on each frame,
FFmpeg handles encoding and audio remux.

Standalone:
    python steps/burn_captions.py --video temp/with_audio.mp4 \
        --srt temp/captions.srt --out temp/captioned.mp4
"""
import sys, subprocess, argparse, re, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ── SRT parser ────────────────────────────────────────────────────────────────

def _srt_time_to_sec(ts: str) -> float:
    """'00:01:23,456'  →  83.456"""
    h, m, rest = ts.split(":")
    s, ms = rest.replace(",", ".").split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(srt_path: Path) -> list[dict]:
    """Return list of {start, end, text} dicts sorted by start time."""
    text = srt_path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", text.strip())
    subs = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        # lines[0] = index, lines[1] = timestamps, lines[2:] = text
        try:
            start_s, end_s = lines[1].split(" --> ")
            subs.append({
                "start": _srt_time_to_sec(start_s.strip()),
                "end":   _srt_time_to_sec(end_s.strip()),
                "text":  " ".join(lines[2:]).strip(),
            })
        except Exception:
            continue
    return sorted(subs, key=lambda x: x["start"])


def _get_sub_at(subs: list[dict], t: float) -> str:
    for sub in subs:
        if sub["start"] <= t < sub["end"]:
            return sub["text"]
    return ""


# ── Font loader ───────────────────────────────────────────────────────────────

def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
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
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


# ── Caption drawer ────────────────────────────────────────────────────────────

def _draw_caption(img: Image.Image, text: str, font: ImageFont.FreeTypeFont, margin_v: int = 160) -> None:
    """
    TikTok-style captions: bold white text, thick black outline, centered,
    with a subtle dark semi-transparent background strip for readability.
    """
    if not text:
        return

    W, H  = img.size
    draw  = ImageDraw.Draw(img, "RGBA")
    max_w = W - 60

    # Word-wrap into lines
    words, lines, cur = text.split(), [], []
    for word in words:
        test = " ".join(cur + [word])
        if draw.textlength(test, font=font) > max_w and cur:
            lines.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(" ".join(cur))

    line_h  = font.size + 12
    total_h = len(lines) * line_h
    y_start = H - margin_v - total_h

    # Draw semi-transparent background strip behind all lines
    strip_pad = 20
    draw.rectangle(
        [0, y_start - strip_pad, W, y_start + total_h + strip_pad],
        fill=(0, 0, 0, 140)
    )

    y = y_start
    for line in lines:
        lw = int(draw.textlength(line, font=font))
        x  = (W - lw) // 2

        # Thick black outline (3px, 8 directions)
        for ox, oy in [(-3,-3),(3,-3),(-3,3),(3,3),(-3,0),(3,0),(0,-3),(0,3)]:
            draw.text((x + ox, y + oy), line, font=font, fill=(0, 0, 0, 255))

        # Bright white text on top
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_h


# ── Video info ────────────────────────────────────────────────────────────────

def _video_info(video_path: Path) -> dict:
    """Return width, height, fps as floats via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", str(video_path),
        ],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            w   = int(stream["width"])
            h   = int(stream["height"])
            fps_s = stream.get("r_frame_rate", "30/1")
            num, den = fps_s.split("/")
            fps = float(num) / float(den)
            return {"width": w, "height": h, "fps": fps}
    raise RuntimeError("Could not find video stream in input file")


# ── Main entry point ──────────────────────────────────────────────────────────

def burn_captions(
    video_path: Path,
    srt_path: Path,
    out_path: Path,
    font_size: int = 58,
    margin_v: int  = 160,
) -> Path:
    """
    Burn SRT captions into video using Pillow frame processing.
    No libass / libfreetype required in FFmpeg.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    subs = parse_srt(srt_path)
    if not subs:
        # No captions — just copy video unchanged
        import shutil
        shutil.copy(video_path, out_path)
        print(f"  ✓ No captions to burn — copied: {out_path.name}")
        return out_path

    info = _video_info(video_path)
    W, H, fps = info["width"], info["height"], info["fps"]
    frame_bytes = W * H * 3
    font = _load_font(font_size)

    print(f"  [Captions] Burning {len(subs)} subtitles via Pillow ({W}×{H} @ {fps:.1f}fps)...")

    # Force exactly 30fps on read — prevents drift on VFR sources
    fps = 30.0

    # ── Reader: video → raw RGB24 frames ─────────────────────────────────────
    reader = subprocess.Popen(
        [
            "ffmpeg", "-i", str(video_path),
            "-vf", "fps=30",                  # force CFR 30fps output
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "pipe:1",
        ],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )

    # Temp video path (no audio — we remux at the end)
    tmp_video = out_path.with_suffix(".tmp.mp4")

    # ── Writer: raw RGB24 frames → H.264 video ────────────────────────────────
    writer = subprocess.Popen(
        [
            "ffmpeg", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(fps),
            "-i", "pipe:0",
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

            t   = frame_num / fps
            sub = _get_sub_at(subs, t)

            img = Image.frombytes("RGB", (W, H), raw)
            if sub:
                _draw_caption(img, sub, font, margin_v)

            writer.stdin.write(img.tobytes())
            frame_num += 1

            if frame_num % 150 == 0:
                print(f"    {frame_num} frames ({t:.1f}s)...")
    except BrokenPipeError:
        pass
    finally:
        writer.stdin.close()
        reader.stdout.close()

    reader.wait()
    writer.wait()

    if writer.returncode != 0:
        tmp_video.unlink(missing_ok=True)
        raise RuntimeError("FFmpeg writer failed during caption burning")

    # ── Remux: copy audio from original video into captioned video ────────────
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(tmp_video),
            "-i", str(video_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "copy",
            str(out_path),
        ],
        capture_output=True, text=True
    )
    tmp_video.unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"Audio remux failed:\n{result.stderr[-400:]}")

    print(f"  ✓ Captions burned: {out_path.name} ({frame_num} frames)")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--srt",   required=True)
    parser.add_argument("--out",   required=True)
    args = parser.parse_args()

    burn_captions(Path(args.video), Path(args.srt), Path(args.out))
