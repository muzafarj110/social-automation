import { useEffect, useState } from "react";
import { listPosts } from "../api.js";

const PLATFORM_LABEL = {
  linkedin: "LinkedIn", twitter: "X", instagram: "Instagram", facebook: "Facebook",
  tiktok: "TikTok", youtube: "YouTube", pinterest: "Pinterest", reddit: "Reddit",
  bluesky: "Bluesky", threads: "Threads", googlebusiness: "Google Business",
  telegram: "Telegram", snapchat: "Snapchat", whatsapp: "WhatsApp", discord: "Discord",
};
const STATUS_CLASS = { published: "published", scheduled: "scheduled", draft: "draft", failed: "failed" };

// A unified, cross-platform agenda: every post grouped by the day it goes out.
export default function Calendar() {
  const [posts, setPosts] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    listPosts().then(setPosts).catch((e) => setErr(e.message));
  }, []);

  if (err) return <div className="error">{err}</div>;
  if (!posts) return <div className="empty">Loading…</div>;
  if (posts.length === 0) {
    return <div className="empty">Nothing on the calendar yet. Create a campaign or a quick post to fill it.</div>;
  }

  // Group by date (scheduled time if set, else created), newest day first for
  // published/past, upcoming days ascending. Simple: sort all by when, group by day.
  const withWhen = posts.map((p) => ({ ...p, when: new Date(p.scheduled_for || p.created_at) }));
  withWhen.sort((a, b) => a.when - b.when);
  const groups = {};
  for (const p of withWhen) {
    const key = p.when.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
    (groups[key] ||= []).push(p);
  }

  return (
    <div>
      {Object.entries(groups).map(([day, items]) => (
        <div className="card" key={day}>
          <h2 style={{ marginTop: 0 }}>{day}</h2>
          <div className="pill-list">
            {items.map((p) => (
              <div className="pill" key={p.id} style={{ alignItems: "center", gap: 10 }}>
                <span className="badge kind">{PLATFORM_LABEL[p.platform] || p.platform}</span>
                <span className="muted" style={{ fontSize: 12, minWidth: 56 }}>
                  {p.scheduled_for ? p.when.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}
                </span>
                <span style={{ flex: 1, fontSize: 13 }}>
                  {(p.body || "").slice(0, 120)}{(p.body || "").length > 120 ? "…" : ""}
                </span>
                <span className={`badge ${STATUS_CLASS[p.status] || ""}`}>{p.status}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
