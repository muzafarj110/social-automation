// Mirrors backend/app/api/analytics.py's _aggregate() so a single platform's
// metrics can be recomputed client-side from the full (untruncated) post list
// returned in a /analytics/zernio response's `data.posts`. The server's
// `summary` field is always the all-platforms merged total.
const METRIC_KEYS = ["impressions", "reach", "likes", "comments", "shares", "saves", "clicks", "views"];

export function aggregatePosts(posts) {
  const totals = Object.fromEntries(METRIC_KEYS.map((k) => [k, 0]));
  const recent = [];
  for (const p of posts) {
    const a = p.analytics || {};
    for (const k of METRIC_KEYS) totals[k] += Number(a[k] || 0);
    const plats = p.platforms || [];
    const url = (plats[0] && plats[0].platformPostUrl) || null;
    recent.push({
      content: (p.content || "").slice(0, 160),
      status: p.status,
      platform: p.platform,
      impressions: a.impressions || 0,
      likes: a.likes || 0,
      comments: a.comments || 0,
      url,
    });
  }
  const denom = posts.length || 1;
  return {
    post_count: posts.length,
    impressions: totals.impressions,
    total_likes: totals.likes,
    total_comments: totals.comments,
    avg_likes: Math.round(totals.likes / denom),
    recent: recent.slice(0, 25),
  };
}

export function filterPostsByPlatform(posts, platform) {
  if (platform === "all") return posts;
  return posts.filter((p) => (p.platform || "linkedin") === platform);
}
