"""
Step 3 — Generate voiceover audio from script text.

Supports two TTS engines:
  edge-tts  — Microsoft Edge TTS (free, pip installable, runs anywhere)
  kokoro    — High-quality local Kokoro TTS (requires manual install)

Engine is set via TTS_ENGINE in .env. Voice via TTS_VOICE.

Standalone:
    python steps/generate_audio.py --text "Hello world" --out temp/test/voice.mp3
    python steps/generate_audio.py --file /path/to/script.txt --out temp/test/voice.mp3
"""
import sys, asyncio, subprocess, argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config as cfg


def _tts_edge(text: str, out_path: Path, voice: str) -> None:
    """Generate audio using edge-tts (async under the hood)."""
    import edge_tts

    async def _run():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(out_path))

    asyncio.run(_run())


def _tts_kokoro(text: str, out_path: Path, voice: str = "am_adam") -> None:
    """Generate audio using Kokoro TTS (local, high quality)."""
    import sys as _sys
    _sys.path.insert(0, "/opt/homebrew/lib/python3.11/site-packages")

    import numpy as np, soundfile as sf
    from kokoro import KPipeline

    pipeline = KPipeline(lang_code="a")
    chunks = []
    for _, _, audio in pipeline(text, voice=voice, speed=1.1):
        chunks.append(audio)

    if not chunks:
        raise RuntimeError("Kokoro produced no audio chunks")

    combined = np.concatenate(chunks)

    # Save as wav first, then convert to mp3 via ffmpeg
    wav_path = out_path.with_suffix(".wav")
    sf.write(str(wav_path), combined, 24000)

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-b:a", "128k", str(out_path)],
        check=True, capture_output=True
    )
    wav_path.unlink(missing_ok=True)


def generate_audio(text: str, out_path: Path, channel: dict | None = None) -> Path:
    """
    Generate voiceover MP3 from text.
    Returns path to the generated MP3 file.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    engine = cfg.TTS_ENGINE
    voice  = (channel or {}).get("tts_voice") or cfg.TTS_VOICE

    print(f"  [Audio] Engine: {engine}, Voice: {voice}")

    if engine == "kokoro":
        _tts_kokoro(text, out_path, voice=voice or "am_adam")
    else:
        # Default: edge-tts
        _tts_edge(text, out_path, voice=voice or "en-US-GuyNeural")

    size_kb = out_path.stat().st_size // 1024
    print(f"  ✓ Audio saved: {out_path.name} ({size_kb}KB)")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="Script text directly")
    group.add_argument("--file", help="Path to script text file")
    parser.add_argument("--out", required=True, help="Output MP3 path")
    args = parser.parse_args()

    text = args.text if args.text else Path(args.file).read_text()
    generate_audio(text, Path(args.out))
