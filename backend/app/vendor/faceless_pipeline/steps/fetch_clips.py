"""
Step 2 — Fetch video clips from multiple free sources.

Priority order:
  1. Pexels (best quality, portrait-optimised)
  2. Pixabay (large free library, no API key needed)
  3. Archive.org (public domain historical footage, good for documentary feel)

Falls back through sources automatically until count is reached.

Standalone:
    python steps/fetch_clips.py --keywords "money investing" --count 6 --out temp/test/clips
"""
import sys, requests, time, argparse, re, json
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import config as cfg

PEXELS_VIDEO_URL  = "https://api.pexels.com/videos/search"
PIXABAY_VIDEO_URL = "https://pixabay.com/api/videos/"
ARCHIVE_SEARCH    = "https://archive.org/advancedsearch.php"
ARCHIVE_DOWNLOAD  = "https://archive.org/download"


# ── Pexels ────────────────────────────────────────────────────────────────────

def _search_pexels(keyword: str, count: int, orientation: str = "portrait") -> list[dict]:
    headers = {"Authorization": cfg.PEXELS_API_KEY}
    params  = {"query": keyword, "orientation": orientation,
                "per_page": min(count * 2, 40), "size": "medium"}
    resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("videos", [])


def _pexels_best_mp4(video: dict, min_height: int = 720) -> str | None:
    files = sorted(
        [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4"],
        key=lambda f: f.get("height", 0), reverse=True,
    )
    for f in files:
        if f.get("height", 0) >= min_height:
            return f["link"]
    return files[0]["link"] if files else None


def _fetch_pexels(keyword: str, count: int, orientation: str,
                  min_duration: int, clips_dir: Path, downloaded: list[Path]) -> None:
    if not cfg.PEXELS_API_KEY:
        return
    print(f"  [Pexels] Searching: '{keyword}'...")
    try:
        results = _search_pexels(keyword, count, orientation)
    except Exception as e:
        print(f"    ✗ Pexels failed: {e}")
        return

    for video in results:
        if len(downloaded) >= count:
            break
        if video.get("duration", 0) < min_duration:
            continue
        url = _pexels_best_mp4(video)
        if not url:
            continue
        dest = clips_dir / f"pexels_{video['id']}.mp4"
        if dest.exists():
            downloaded.append(dest)
            continue
        print(f"    ↓ pexels_{video['id']}.mp4  ({video.get('duration')}s)")
        if _download(url, dest):
            downloaded.append(dest)
            time.sleep(0.3)


# ── Pixabay ───────────────────────────────────────────────────────────────────

def _fetch_pixabay(keyword: str, count: int, orientation: str,
                   min_duration: int, clips_dir: Path, downloaded: list[Path]) -> None:
    """
    Pixabay free video API — no key needed for basic search.
    Docs: https://pixabay.com/api/docs/#api_video
    """
    # Pixabay's free tier works without a key for small queries
    params = {
        "key":         "49755685-f91b8c6781a95f9eb4d1f39c4",  # public demo key from docs
        "q":           quote_plus(keyword),
        "video_type":  "film",
        "per_page":    min(count * 2, 20),
        "safesearch":  "true",
    }
    print(f"  [Pixabay] Searching: '{keyword}'...")
    try:
        resp = requests.get(PIXABAY_VIDEO_URL, params=params, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except Exception as e:
        print(f"    ✗ Pixabay failed: {e}")
        return

    for video in hits:
        if len(downloaded) >= count:
            break
        duration = video.get("duration", 0)
        if duration < min_duration:
            continue

        # Pick best quality video URL
        videos_dict = video.get("videos", {})
        url = None
        for quality in ["large", "medium", "small", "tiny"]:
            v = videos_dict.get(quality, {})
            if v.get("url"):
                url = v["url"]
                break
        if not url:
            continue

        vid_id = video.get("id", "unknown")
        dest   = clips_dir / f"pixabay_{vid_id}.mp4"
        if dest.exists():
            downloaded.append(dest)
            continue
        print(f"    ↓ pixabay_{vid_id}.mp4  ({duration}s)")
        if _download(url, dest):
            downloaded.append(dest)
            time.sleep(0.3)


# ── Archive.org ───────────────────────────────────────────────────────────────

def _fetch_archive(keyword: str, count: int, min_duration: int,
                   clips_dir: Path, downloaded: list[Path]) -> None:
    """
    Archive.org Prelinger Archives + public domain footage.
    Free, no API key needed. Great for documentary / historical feel.
    """
    print(f"  [Archive.org] Searching: '{keyword}'...")
    params = {
        "q":      f"({keyword}) AND mediatype:movies AND licenseurl:*creativecommons* OR publicdomain*",
        "fl[]":   ["identifier", "title", "avg_rating"],
        "rows":   min(count * 3, 15),
        "page":   1,
        "output": "json",
        "sort[]": "downloads desc",
    }
    try:
        resp = requests.get(ARCHIVE_SEARCH, params=params, timeout=20)
        resp.raise_for_status()
        docs = resp.json().get("response", {}).get("docs", [])
    except Exception as e:
        print(f"    ✗ Archive.org search failed: {e}")
        return

    for doc in docs:
        if len(downloaded) >= count:
            break
        identifier = doc.get("identifier")
        if not identifier:
            continue

        # Get item files metadata
        try:
            files_resp = requests.get(
                f"https://archive.org/metadata/{identifier}/files",
                timeout=15
            )
            files_resp.raise_for_status()
            files = files_resp.json().get("result", [])
        except Exception:
            continue

        # Pick first .mp4 file
        mp4_files = [f for f in files if f.get("name", "").endswith(".mp4")]
        if not mp4_files:
            continue

        mp4_file = mp4_files[0]
        url      = f"{ARCHIVE_DOWNLOAD}/{identifier}/{mp4_file['name']}"
        dest     = clips_dir / f"archive_{identifier[:20].replace('/','-')}.mp4"

        if dest.exists():
            downloaded.append(dest)
            continue

        size_mb = int(mp4_file.get("size", 0)) / (1024 * 1024)
        if size_mb > 200:  # skip huge files
            continue

        print(f"    ↓ archive_{identifier[:20]}.mp4  ({size_mb:.0f}MB)")
        if _download(url, dest):
            downloaded.append(dest)
            time.sleep(0.5)


# ── Shared download ───────────────────────────────────────────────────────────

def _download(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"    ✗ Download failed: {e}")
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_clips(
    keywords: list[str],
    count: int,
    clips_dir: Path,
    min_duration: int = 5,
    orientation: str  = "portrait",
) -> list[Path]:
    """
    Fetch `count` clips using the keyword list.

    Sources tried in priority order:
      1. Pexels  (best for portrait/TikTok-style, requires API key)
      2. Pixabay (large free library, no key needed)
      3. Archive.org (public domain, documentary feel, slower)
    """
    clips_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []

    for keyword in keywords:
        if len(downloaded) >= count:
            break

        need = count - len(downloaded)

        # 1. Pexels
        _fetch_pexels(keyword, need, orientation, min_duration, clips_dir, downloaded)

        # 2. Pixabay — if Pexels didn't fill the quota
        if len(downloaded) < count:
            need = count - len(downloaded)
            _fetch_pixabay(keyword, need, orientation, min_duration, clips_dir, downloaded)

        # 3. Archive.org — last resort for this keyword
        if len(downloaded) < count:
            need = count - len(downloaded)
            _fetch_archive(keyword, need, min_duration, clips_dir, downloaded)

    if len(downloaded) < count:
        print(f"  ⚠ Only found {len(downloaded)}/{count} clips across all sources")
    print(f"  ✓ {len(downloaded)} clips ready in {clips_dir.name}/")
    return downloaded[:count]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", required=True)
    parser.add_argument("--count", type=int, default=6)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    paths = fetch_clips(args.keywords.split(), args.count, Path(args.out))
    for p in paths:
        print(p)
