"""
Quality validation — runs ffprobe checks on a finished video before it's
saved to the output folder.

Checks:
  - File exists and is non-empty
  - Video stream: correct resolution, minimum duration, sane FPS
  - Audio stream: present, reasonable loudness (not silent, not clipping)
  - Container: valid MP4, no codec errors

Returns a ValidationResult with pass/fail + reasons.
"""
import sys, subprocess, json, math
from pathlib import Path
from dataclasses import dataclass, field

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import config as cfg


@dataclass
class ValidationResult:
    passed: bool
    checks: dict[str, bool]   = field(default_factory=dict)
    warnings: list[str]       = field(default_factory=list)
    errors: list[str]         = field(default_factory=list)

    def summary(self) -> str:
        icon = "✅" if self.passed else "❌"
        lines = [f"  {icon} Quality validation: {'PASSED' if self.passed else 'FAILED'}"]
        for name, ok in self.checks.items():
            lines.append(f"    {'✓' if ok else '✗'} {name}")
        for w in self.warnings:
            lines.append(f"    ⚠ {w}")
        for e in self.errors:
            lines.append(f"    ✗ {e}")
        return "\n".join(lines)


def _ffprobe(path: Path) -> dict:
    """Run ffprobe and return full stream/format info as dict."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            str(path),
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[:200]}")
    return json.loads(result.stdout)


def _measure_loudness(path: Path) -> float | None:
    """Use ffmpeg's loudnorm to measure integrated loudness (LUFS). Returns None on error."""
    result = subprocess.run(
        [
            "ffmpeg", "-i", str(path),
            "-af", "loudnorm=print_format=json",
            "-f", "null", "-",
        ],
        capture_output=True, text=True
    )
    # loudnorm prints JSON to stderr
    stderr = result.stderr
    try:
        # Find the JSON block in stderr output
        start = stderr.rfind("{")
        end   = stderr.rfind("}") + 1
        if start == -1:
            return None
        data = json.loads(stderr[start:end])
        lufs = float(data.get("input_i", "-99"))
        return lufs
    except Exception:
        return None


def validate_video(
    path: Path,
    mode: str = "short",
    min_duration: float = 30.0,
    max_duration: float = 400.0,
    expected_width: int  = cfg.VIDEO_WIDTH,
    expected_height: int = cfg.VIDEO_HEIGHT,
    min_lufs: float = -40.0,   # quieter than this = probably silent
    max_lufs: float = -6.0,    # louder than this = probably clipping
) -> ValidationResult:
    """
    Run quality checks on a finished output video.
    Returns ValidationResult — check .passed and .summary().
    """
    checks   = {}
    warnings = []
    errors   = []

    # ── 1. File exists and is non-empty ───────────────────────────────────────
    if not path.exists():
        return ValidationResult(
            passed=False, errors=["File does not exist"]
        )
    size_mb = path.stat().st_size / (1024 * 1024)
    checks["file_exists"] = True
    if size_mb < 0.5:
        errors.append(f"File too small ({size_mb:.2f}MB) — likely corrupt")
        checks["file_size_ok"] = False
    else:
        checks["file_size_ok"] = True

    # ── 2. Parse streams ──────────────────────────────────────────────────────
    try:
        probe = _ffprobe(path)
    except Exception as e:
        return ValidationResult(passed=False, errors=[f"ffprobe failed: {e}"])

    streams  = probe.get("streams", [])
    fmt      = probe.get("format", {})
    duration = float(fmt.get("duration", 0))

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    # ── 3. Video stream ───────────────────────────────────────────────────────
    if not video_streams:
        errors.append("No video stream found")
        checks["has_video"] = False
    else:
        checks["has_video"] = True
        vs  = video_streams[0]
        vw  = int(vs.get("width",  0))
        vh  = int(vs.get("height", 0))
        fps_s = vs.get("r_frame_rate", "0/1")
        try:
            num, den = fps_s.split("/")
            fps = float(num) / float(den)
        except Exception:
            fps = 0

        # Resolution
        res_ok = (vw == expected_width and vh == expected_height)
        checks["resolution_correct"] = res_ok
        if not res_ok:
            errors.append(f"Wrong resolution: {vw}×{vh} (expected {expected_width}×{expected_height})")

        # FPS
        fps_ok = 24 <= fps <= 60
        checks["fps_ok"] = fps_ok
        if not fps_ok:
            warnings.append(f"Unusual FPS: {fps:.1f}")

        # Codec
        codec_ok = vs.get("codec_name") in ("h264", "hevc", "vp9", "av1")
        checks["video_codec_ok"] = codec_ok
        if not codec_ok:
            warnings.append(f"Unusual video codec: {vs.get('codec_name')}")

    # ── 4. Audio stream ───────────────────────────────────────────────────────
    if not audio_streams:
        errors.append("No audio stream found")
        checks["has_audio"] = False
    else:
        checks["has_audio"] = True
        as_ = audio_streams[0]
        checks["audio_codec_ok"] = as_.get("codec_name") in ("aac", "mp3", "opus", "vorbis")

    # ── 5. Duration ───────────────────────────────────────────────────────────
    dur_ok = min_duration <= duration <= max_duration
    checks["duration_ok"] = dur_ok
    if not dur_ok:
        errors.append(f"Duration {duration:.1f}s out of expected range [{min_duration}–{max_duration}s]")

    # ── 6. Audio loudness (skip if no audio) ─────────────────────────────────
    if audio_streams:
        lufs = _measure_loudness(path)
        if lufs is not None:
            silent   = lufs < min_lufs
            clipping = lufs > max_lufs
            checks["audio_not_silent"]   = not silent
            checks["audio_not_clipping"] = not clipping
            if silent:
                errors.append(f"Audio too quiet ({lufs:.1f} LUFS) — voiceover may be missing")
            elif clipping:
                warnings.append(f"Audio loud ({lufs:.1f} LUFS) — check mix levels")
        else:
            warnings.append("Could not measure audio loudness")

    passed = len(errors) == 0
    return ValidationResult(passed=passed, checks=checks, warnings=warnings, errors=errors)


def validate_all_outputs(outputs: dict, mode: str = "both") -> dict[str, ValidationResult]:
    """
    Validate all video outputs from a pipeline run.
    outputs: dict of {key: Path}, e.g. {"video_short": Path(...), "video_long": Path(...)}
    Returns dict of {key: ValidationResult}.
    """
    results = {}
    for key, path in outputs.items():
        if not str(path).endswith(".mp4"):
            continue
        m = "short" if "short" in key else "long"
        min_dur = 30  if m == "short" else 120
        max_dur = 120 if m == "short" else 400
        print(f"  Validating {key}...")
        result = validate_video(Path(path), mode=m, min_duration=min_dur, max_duration=max_dur)
        print(result.summary())
        results[key] = result

    all_passed = all(r.passed for r in results.values())
    if all_passed:
        print("  ✅ All outputs passed quality checks")
    else:
        failed = [k for k, r in results.items() if not r.passed]
        print(f"  ❌ Failed: {', '.join(failed)}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    args = parser.parse_args()
    result = validate_video(Path(args.video))
    print(result.summary())
    sys.exit(0 if result.passed else 1)
