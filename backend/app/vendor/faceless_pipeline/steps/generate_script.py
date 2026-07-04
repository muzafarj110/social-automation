"""
Step 1 — Script generation.

Two modes:
  LLM-auto: the model generates topic, Pexels keywords, short + long scripts.
  Manual:      Reads a plain text file passed via --script flag.

Standalone:
    python steps/generate_script.py --channel finance
    python steps/generate_script.py --channel finance --topic "5 money mistakes"
    python steps/generate_script.py --channel finance --script /path/to/script.txt

NOTE (Autopilot integration): the LLM call goes through OpenRouter (OpenAI-
compatible REST), not the Anthropic SDK, so the free model configured via
SCRIPT_LLM_MODEL can be swapped with a single env var if it's ever
deprecated/rate-limited — see _call_llm() below.
"""
import sys, json, argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config as cfg


SCRIPT_PROMPT = """You are generating a faceless video script for the YouTube/TikTok channel {handle}.

Channel niche: {niche}
Topic: {topic}

{system_prompt}

Generate TWO versions of the script:
1. SHORT (45-60 seconds when read aloud at normal pace, ~100-120 words)
2. LONG (3-4 minutes when read aloud, ~450-550 words)

Also generate ALL of the following:
- A punchy video TITLE (max 60 chars, written for clicks and YouTube SEO)
- 3 Pexels search KEYWORDS (single words or short phrases for stock footage search)
- 20 HASHTAGS (mix of broad + niche, no spaces, for TikTok/YouTube use)
- A YOUTUBE_TITLE (max 60 chars, keyword-rich for YouTube search ranking — can differ from title)
- A YOUTUBE_DESCRIPTION (3–4 sentences, keyword-rich, starts with a hook, includes a call to action)
- A TIKTOK_CAPTION (under 130 chars hook sentence + top 5 hashtags)
- A HOOK_TEXT (max 8 words, punchy scroll-stopping opener shown as full-screen text — make it shocking, bold, or provocative. NO punctuation except a question mark if needed.)

Return ONLY valid JSON, no markdown:
{{
  "title": "...",
  "pexels_keywords": ["keyword1", "keyword2", "keyword3"],
  "short_script": "Full short script text here...",
  "long_script": "Full long script text here...",
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "youtube_title": "...",
  "youtube_description": "...",
  "tiktok_caption": "...",
  "hook_text": "..."
}}"""

TOPIC_PROMPT = """You are a viral content strategist for the YouTube/TikTok channel {handle}.
Channel niche: {niche}

Suggest the single best video topic right now — high search volume, trending, and easy to cover with stock footage.
Return ONLY a short topic description (max 15 words), no explanation."""


def _call_llm(prompt: str) -> str:
    """Calls the configured free model via OpenRouter's OpenAI-compatible API.
    SCRIPT_LLM_MODEL is env-driven so a deprecated/rate-limited free model can
    be swapped without touching this code."""
    import openai
    client = openai.OpenAI(
        api_key=cfg.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
    resp = client.chat.completions.create(
        model=cfg.SCRIPT_LLM_MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


def _strip_fences(raw: str) -> str:
    import re
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    return re.sub(r"\s*```$", "", raw)


def _call_llm_json(prompt: str) -> dict:
    """Free models are less reliably strict-JSON than Claude was — one repair
    retry before giving up, since a stray sentence before/after the JSON is a
    common failure mode for smaller models."""
    import json
    raw = _strip_fences(_call_llm(prompt))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        repair_prompt = (
            "Your previous response was not valid JSON. Return ONLY the "
            f"corrected valid JSON, nothing else:\n\n{raw}"
        )
        raw = _strip_fences(_call_llm(repair_prompt))
        return json.loads(raw)


def auto_pick_topic(channel: dict) -> str:
    """Ask Claude to pick a trending topic for this channel."""
    prompt = TOPIC_PROMPT.format(
        handle=channel["handle"],
        niche=channel["niche"],
    )
    topic = _call_llm(prompt)
    print(f"  Claude picked topic: {topic}")
    return topic


def generate_script(channel: dict, topic: str | None = None, script_file: str | None = None) -> dict:
    """
    Returns a dict with keys: title, pexels_keywords, short_script, long_script.

    If script_file is given, reads it and uses Claude only for title + keywords.
    If topic is None, Claude picks a topic first.
    """
    print("[Script] Generating script...")

    # Manual script path
    if script_file:
        script_path = Path(script_file)
        if not script_path.exists():
            raise FileNotFoundError(f"Script file not found: {script_file}")
        manual_text = script_path.read_text().strip()
        # Still use Claude to extract title + keywords from manual script
        extract_prompt = f"""Given this video script, extract:
- A punchy video title (max 60 chars)
- 3 Pexels search keywords matching the visual content

Script:
{manual_text[:800]}

Return ONLY JSON: {{"title": "...", "pexels_keywords": ["kw1", "kw2", "kw3"]}}"""
        meta = _call_llm_json(extract_prompt)
        return {
            "title":               meta["title"],
            "pexels_keywords":     meta["pexels_keywords"],
            "short_script":        manual_text,
            "long_script":         manual_text,
            "hashtags":            meta.get("hashtags", []),
            "youtube_title":       meta.get("youtube_title", meta["title"]),
            "youtube_description": meta.get("youtube_description", ""),
            "tiktok_caption":      meta.get("tiktok_caption", ""),
        }

    # Claude-auto path
    if not topic:
        topic = auto_pick_topic(channel)

    prompt = SCRIPT_PROMPT.format(
        handle=channel["handle"],
        niche=channel["niche"],
        topic=topic,
        system_prompt=channel.get("claude_system_prompt", ""),
    )

    result = _call_llm_json(prompt)

    print(f"  Title: {result['title']}")
    print(f"  Keywords: {result['pexels_keywords']}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True)
    parser.add_argument("--topic", default=None)
    parser.add_argument("--script", default=None, help="Path to manual script file")
    args = parser.parse_args()

    channel = cfg.load_channel(args.channel)
    result = generate_script(channel, topic=args.topic, script_file=args.script)
    print(json.dumps(result, indent=2))
