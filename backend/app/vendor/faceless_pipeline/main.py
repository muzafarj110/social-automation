#!/usr/bin/env python3
"""
Faceless Video Pipeline — Master Orchestration

Usage:
    # Claude picks topic automatically
    python main.py --channel finance --mode both

    # You provide the topic
    python main.py --channel ai_tools --topic "5 free AI tools in 2025" --mode short

    # You provide a full script file
    python main.py --channel health --script /path/to/script.txt --mode long

    # Keep temp files for debugging
    python main.py --channel finance --mode short --keep-temp
"""
import sys, shutil, time, argparse, json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import config as cfg
from steps.generate_script     import generate_script
from steps.fetch_clips         import fetch_clips
from steps.generate_audio      import generate_audio
from steps.render_intro_outro  import render_intro, render_outro, render_hook_screen
from steps.merge_clips         import merge_clips
from steps.mix_audio           import mix_audio
from steps.generate_captions   import generate_captions
from steps.burn_captions       import burn_captions
from steps.add_watermark       import add_watermark
from steps.generate_thumbnail  import generate_thumbnail
from steps.validate_output     import validate_all_outputs


def _step(n: int, total: int, label: str) -> None:
    print(f"\n[{n}/{total}] {label}")
    print("─" * 50)


def run_pipeline(
    channel_name: str,
    topic: str | None,
    mode: str,
    script_file: str | None,
    keep_temp: bool,
) -> dict:
    """
    Run the full pipeline for a channel.
    Returns a summary dict with output file paths.
    """
    start_time = time.time()

    # ── Setup ──────────────────────────────────────────────────────────────────
    cfg.validate()
    channel  = cfg.load_channel(channel_name)
    run_id   = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths    = cfg.get_paths(channel_name, run_id)
    modes    = ["short", "long"] if mode == "both" else [mode]

    print(f"\n{'═'*56}")
    print(f"  CHANNEL : {channel['name']}  ({channel['handle']})")
    print(f"  NICHE   : {channel['niche']}")
    print(f"  MODE    : {mode}")
    print(f"  RUN ID  : {run_id}")
    print(f"{'═'*56}")

    total_steps = 11
    step = 0

    # ── 1. Generate Script ─────────────────────────────────────────────────────
    step += 1
    _step(step, total_steps, "Script generation")
    script_data = generate_script(channel, topic=topic, script_file=script_file)
    title    = script_data["title"]
    keywords = script_data["pexels_keywords"]

    # Save script data to temp for reference
    (paths["temp"] / "script.json").write_text(json.dumps(script_data, indent=2))
    print(f"  Title: {title}")

    # ── 2. Fetch Clips ─────────────────────────────────────────────────────────
    step += 1
    _step(step, total_steps, "Fetching Pexels clips")

    # Fetch the max clips needed (long mode needs more)
    max_clips = channel.get("long_clips", 18) if "long" in modes else channel.get("short_clips", 6)
    all_keywords = keywords + channel.get("pexels_fallback_keywords", [])

    clips = fetch_clips(
        keywords=all_keywords,
        count=max_clips,
        clips_dir=paths["clips_dir"],
        min_duration=5,
        orientation=channel.get("pexels_orientation", "portrait"),
    )

    short_clips = clips[:channel.get("short_clips", 6)]
    long_clips  = clips[:channel.get("long_clips", 18)]

    # ── 3. Generate Audio ──────────────────────────────────────────────────────
    step += 1
    _step(step, total_steps, "Generating voiceover audio")

    if "short" in modes:
        generate_audio(script_data["short_script"], paths["voiceover_s"], channel)
    if "long" in modes:
        generate_audio(script_data["long_script"],  paths["voiceover_l"], channel)

    # ── 4. Render Intro / Outro ────────────────────────────────────────────────
    step += 1
    _step(step, total_steps, "Rendering hook + intro + outro cards")
    hook_text = script_data.get("hook_text", title)
    # Use first Pexels clip as dynamic hook background for visual impact
    hook_bg = clips[0] if clips else None
    render_hook_screen(hook_text, channel["accent_color"], paths["temp"] / "hook.mp4",
                       bg_clip=hook_bg)
    render_intro(title, channel["handle"], channel["accent_color"], paths["intro"])
    render_outro(channel["handle"], channel["accent_color"], paths["outro"])

    clip_duration = channel.get("clip_duration", 8)
    music_dir     = paths["music_dir"]
    music_style   = channel.get("music_style", "calm")

    outputs: dict[str, Path] = {}

    for m in modes:
        clips_for_mode = short_clips if m == "short" else long_clips
        voice_path     = paths["voiceover_s"] if m == "short" else paths["voiceover_l"]
        suffix         = f"_{m}"

        print(f"\n  ── Processing {m.upper()} version ({len(clips_for_mode)} clips) ──")

        # ── 5. Merge Clips ─────────────────────────────────────────────────────
        merged = merge_clips(clips_for_mode, paths["intro"], paths["outro"],
                              paths[f"merged_{m[0]}"], clip_duration,
                              hook=paths["temp"] / "hook.mp4")

        # ── 6. Mix Audio ───────────────────────────────────────────────────────
        mixed = mix_audio(merged, voice_path, paths[f"mixed_{m[0]}"],
                          music_dir, music_style)

        # ── 7. Generate Captions ───────────────────────────────────────────────
        srt_path = paths[f"captions_{m[0]}"]
        generate_captions(voice_path, srt_path)

        # ── 8. Burn Captions ───────────────────────────────────────────────────
        captioned = burn_captions(mixed, srt_path, paths[f"captioned_{m[0]}"])

        # ── 9. Add Watermark ───────────────────────────────────────────────────
        watermarked = add_watermark(captioned, paths["logo"], paths[f"watermarked_{m[0]}"])

        # ── 10. Copy to Output ─────────────────────────────────────────────────
        safe_title  = title[:40].replace(" ", "_").replace("/", "-")
        final_video = paths["output"] / f"{safe_title}_{run_id}{suffix}.mp4"
        final_srt   = paths["output"] / f"{safe_title}_{run_id}{suffix}.srt"
        shutil.copy(watermarked, final_video)
        shutil.copy(srt_path,    final_srt)

        outputs[f"video_{m}"] = final_video
        outputs[f"srt_{m}"]   = final_srt

    # ── Thumbnail (from short or long video) ──────────────────────────────────
    step += 1
    _step(step, total_steps, "Generating thumbnail")
    src_for_thumb = outputs.get("video_short") or outputs.get("video_long")
    thumb_path = paths["output"] / f"{safe_title}_{run_id}.jpg"
    generate_thumbnail(
        src_for_thumb, title, thumb_path,
        accent=channel["accent_color"],
        fonts_dir=paths["fonts_dir"],
    )
    outputs["thumbnail"] = thumb_path

    # ── Quality validation ─────────────────────────────────────────────────────
    step += 1
    _step(step, total_steps, "Quality validation")
    validation = validate_all_outputs(outputs, mode=mode)
    failed_keys = [k for k, r in validation.items() if not r.passed]
    if failed_keys:
        print(f"\n  ⚠ Some outputs failed validation: {failed_keys}")
        print("    Videos saved anyway — check errors above before posting.")

    # ── Save metadata JSON next to output videos ───────────────────────────────
    meta_path = paths["output"] / f"{safe_title}_{run_id}_metadata.json"
    meta_path.write_text(json.dumps({
        **script_data,
        "channel":  channel_name,
        "run_id":   run_id,
        "outputs":  {k: str(v) for k, v in outputs.items()},
    }, indent=2))
    outputs["metadata"] = meta_path

    # ── Cleanup temp ──────────────────────────────────────────────────────────
    if not keep_temp:
        shutil.rmtree(paths["temp"], ignore_errors=True)
        print(f"\n  ✓ Temp files cleaned up")

    elapsed = int(time.time() - start_time)
    print(f"\n{'═'*56}")
    print(f"  DONE in {elapsed}s")
    for key, path in outputs.items():
        size_mb = path.stat().st_size / (1024 * 1024) if path.exists() else 0
        print(f"  {key:14s}: {path.name}  ({size_mb:.1f}MB)")
    print(f"{'═'*56}\n")

    return outputs


def main():
    parser = argparse.ArgumentParser(
        description="Faceless Video Pipeline — generate YouTube/TikTok videos automatically"
    )
    parser.add_argument("--channel",    required=True,
                        help="Channel name — must match a file in channels/*.yaml")
    parser.add_argument("--topic",      default=None,
                        help="Video topic (Claude picks one if not provided)")
    parser.add_argument("--script",     default=None,
                        help="Path to a manual script .txt file")
    parser.add_argument("--mode",       choices=["short", "long", "both"], default="both",
                        help="Video length: short (45-60s), long (3-5min), or both")
    parser.add_argument("--keep-temp",  action="store_true",
                        help="Keep /temp/ files after pipeline finishes")
    args = parser.parse_args()

    run_pipeline(
        channel_name=args.channel,
        topic=args.topic,
        mode=args.mode,
        script_file=args.script,
        keep_temp=args.keep_temp,
    )


if __name__ == "__main__":
    main()
