// Shared platform id -> display label lookup (mirrors the list in Accounts.jsx
// and Posts.jsx). New surfaces that show a platform badge should import this
// instead of duplicating the map again.
export const PLATFORM_LABEL = {
  linkedin: "LinkedIn", twitter: "X", instagram: "Instagram", facebook: "Facebook",
  tiktok: "TikTok", youtube: "YouTube", pinterest: "Pinterest", reddit: "Reddit",
  bluesky: "Bluesky", threads: "Threads", googlebusiness: "Google Business",
  telegram: "Telegram", snapchat: "Snapchat", whatsapp: "WhatsApp", discord: "Discord",
};

export function platformLabel(id) {
  return PLATFORM_LABEL[id] || id || "Unknown";
}

// Short 2-3 letter codes for space-constrained UI (calendar day chips).
const PLATFORM_SHORT = {
  linkedin: "in", twitter: "x", instagram: "ig", facebook: "fb",
  tiktok: "tt", youtube: "yt", pinterest: "pin", reddit: "rd",
  bluesky: "bsky", threads: "th", googlebusiness: "gb",
  telegram: "tg", snapchat: "sc", whatsapp: "wa", discord: "dc",
};

export function platformShort(id) {
  return PLATFORM_SHORT[id] || (id ? id.slice(0, 2) : "?");
}

// Platforms that report reach as "views" rather than "impressions" — mirrors
// VIEW_BASED_PLATFORMS in backend/app/api/analytics.py. Showing a video
// platform's real view count under an "Impressions" label misrepresents
// what was actually measured.
const VIEW_BASED_PLATFORMS = new Set(["youtube", "tiktok"]);

export function reachMetricLabel(platform) {
  return VIEW_BASED_PLATFORMS.has(platform) ? "Views" : "Impressions";
}
