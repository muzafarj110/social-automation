"""
Step 7 — Transcribe voiceover and generate SRT captions.

Auto-detects Apple Silicon → mlx-whisper (fast Neural Engine).
Falls back to openai-whisper on other platforms.

Standalone:
    python steps/generate_captions.py --audio temp/voiceover.mp3 --out temp/captions.srt
"""
import sys, subprocess, argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config as cfg


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp HH:MM:SS,mmm."""
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _segments_to_srt(segments: list[dict]) -> str:
    """Convert Whisper segments list to SRT format string."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _seconds_to_srt_time(seg["start"])
        end   = _seconds_to_srt_time(seg["end"])
        text  = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def _resample_for_whisper(audio_path: Path) -> Path:
    """Resample audio to 16kHz mono WAV (Whisper's preferred format)."""
    resampled = audio_path.parent / f"{audio_path.stem}_16k.wav"
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(audio_path),
         "-ar", "16000", "-ac", "1", str(resampled)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Resample failed: {result.stderr[-400:]}")
    return resampled


def generate_captions(audio_path: Path, out_srt: Path) -> Path:
    """
    Transcribe audio and write SRT file.
    Returns path to the .srt file.
    """
    out_srt.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [Captions] Backend: {cfg.WHISPER_BACKEND}, model: {cfg.WHISPER_MODEL}")

    # Resample audio to 16kHz for Whisper
    wav_path = _resample_for_whisper(audio_path)

    if cfg.WHISPER_BACKEND == "mlx-whisper":
        import mlx_whisper
        model_repo = f"mlx-community/whisper-{cfg.WHISPER_MODEL}-mlx"
        result = mlx_whisper.transcribe(str(wav_path), path_or_hf_repo=model_repo)
    else:
        import whisper
        model  = whisper.load_model(cfg.WHISPER_MODEL)
        result = model.transcribe(str(wav_path))

    wav_path.unlink(missing_ok=True)  # clean up resampled file

    segments = result.get("segments", [])
    if not segments:
        raise RuntimeError("Whisper returned no segments — check audio file")

    srt_content = _segments_to_srt(segments)
    out_srt.write_text(srt_content, encoding="utf-8")

    print(f"  ✓ Captions: {out_srt.name} ({len(segments)} segments)")
    return out_srt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--out",   required=True)
    args = parser.parse_args()

    generate_captions(Path(args.audio), Path(args.out))
