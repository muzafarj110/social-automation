import { useEffect, useState } from "react";
import {
  listPosts, syncPosts, publishPost, schedulePost, deletePost, getPostInfographic, updatePost,
} from "../api.js";

const MEDIA_REQUIRED = new Set(["instagram", "tiktok", "youtube", "pinterest", "snapchat"]);
const PLATFORM_LABEL = {
  linkedin: "LinkedIn", twitter: "X", instagram: "Instagram", facebook: "Facebook",
  tiktok: "TikTok", youtube: "YouTube", pinterest: "Pinterest", reddit: "Reddit",
  bluesky: "Bluesky", threads: "Threads", googlebusiness: "Google Business",
  telegram: "Telegram", snapchat: "Snapchat", whatsapp: "WhatsApp", discord: "Discord",
};
const FILTERS = [
  ["all", "All"], ["draft", "Drafts"], ["scheduled", "Scheduled"],
  ["published", "Published"], ["failed", "Failed"],
];

function PostCard({ post, onChange }) {
  const [when, setWhen] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [mediaUrl, setMediaUrl] = useState("");

  const hasMedia = Array.isArray(post.media) && post.media.length > 0;
  const needsMedia = MEDIA_REQUIRED.has(post.platform) && !hasMedia;

  const viewInfographic = async () => {
    setError("");
    try {
      const { html } = await getPostInfographic(post.id);
      const w = window.open("", "_blank");
      if (w) { w.document.write(html || ""); w.document.close(); }
    } catch (e) { setError(e.message); }
  };

  const act = (fn) => async () => {
    setError("");
    setBusy(true);
    try {
      await fn();
      onChange();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const doSchedule = act(async () => {
    if (!when) throw new Error("Pick a date and time.");
    // datetime-local has no timezone; send as ISO with local offset.
    const iso = new Date(when).toISOString();
    await schedulePost(post.id, iso, "UTC");
  });

  const published = post.status === "published";
  const scheduled = post.status === "scheduled";
  const editable = !published && !scheduled; // draft or failed

  return (
    <div className="card">
      <div className="row">
        <span className="badge kind">{PLATFORM_LABEL[post.platform] || post.platform}</span>
        <span className={`badge ${post.status}`}>{post.status}</span>
        {hasMedia && <span className="badge published">📷 media</span>}
        {post.scheduled_for && (
          <span className="muted">for {new Date(post.scheduled_for).toLocaleString()}</span>
        )}
        {post.has_infographic && (
          <button className="btn-ghost" style={{ padding: "2px 8px", fontSize: 12 }} onClick={viewInfographic}>
            View infographic
          </button>
        )}
        <div className="spacer" />
        {post.platform_post_url && (
          <a href={post.platform_post_url} target="_blank" rel="noreferrer"
             style={{ color: "var(--teal)", fontSize: 13, fontWeight: 600 }}>
            View on LinkedIn ↗
          </a>
        )}
      </div>

      <div className="post-body">{post.body}</div>
      {post.hashtags?.length > 0 && (
        <div className="hashtags">{post.hashtags.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" ")}</div>
      )}
      {post.error && <div className="error">{post.error}</div>}
      {error && <div className="error">{error}</div>}

      {editable && (MEDIA_REQUIRED.has(post.platform) || hasMedia) && (
        <div style={{ marginTop: 12, padding: "10px 12px", borderRadius: 8,
                      background: needsMedia ? "#fff7ed" : "#f6f7fb" }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
            {needsMedia
              ? `${PLATFORM_LABEL[post.platform] || post.platform} needs an image or video to publish`
              : "Media attached"}
          </div>
          {hasMedia && (
            <div className="muted" style={{ fontSize: 12, marginBottom: 6, wordBreak: "break-all" }}>
              {post.media.map((m) => m.url).filter(Boolean).join(", ")}
            </div>
          )}
          <div className="row">
            <input style={{ flex: 1 }} placeholder="Paste an image or video URL…"
              value={mediaUrl} onChange={(e) => setMediaUrl(e.target.value)} />
            <button className="btn-secondary" disabled={busy || !mediaUrl.trim()}
              onClick={act(async () => {
                await updatePost(post.id, { media: [{ type: "image", url: mediaUrl.trim() }] });
                setMediaUrl("");
              })}>
              {hasMedia ? "Replace media" : "Attach media"}
            </button>
          </div>
        </div>
      )}

      {editable && (
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn-primary" disabled={busy || needsMedia} onClick={act(() => publishPost(post.id))}>
            Publish now
          </button>
          <input
            type="datetime-local"
            style={{ width: 220 }}
            value={when}
            onChange={(e) => setWhen(e.target.value)}
          />
          <button className="btn-secondary" disabled={busy || needsMedia} onClick={doSchedule}>
            Schedule
          </button>
          <div className="spacer" />
          <button className="btn-ghost" disabled={busy} onClick={act(() => deletePost(post.id))}>
            Delete
          </button>
        </div>
      )}

      {scheduled && (
        <div className="row" style={{ marginTop: 12 }}>
          <span className="muted">Scheduled — it will publish automatically at the time above.</span>
          <div className="spacer" />
          <button className="btn-ghost" disabled={busy} onClick={act(() => deletePost(post.id))}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

export default function Posts({ refreshKey }) {
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [filter, setFilter] = useState("all");

  const load = async () => {
    setError("");
    try {
      setPosts(await listPosts());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Refresh reconciles scheduled posts with Zernio (did they publish / fail?).
  const refresh = async () => {
    setError("");
    setSyncing(true);
    try {
      setPosts(await syncPosts());
    } catch (e) {
      setError(e.message);
    } finally {
      setSyncing(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [refreshKey]); // eslint-disable-line

  if (loading) return <div className="empty">Loading…</div>;

  const shown = filter === "all" ? posts : posts.filter((p) => p.status === filter);

  return (
    <>
      {error && <div className="error">{error}</div>}
      <div className="row" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0, color: "var(--blue)" }}>Your posts</h2>
        <div className="spacer" />
        <button className="btn-secondary" disabled={syncing} onClick={refresh}>
          {syncing ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      {posts.length === 0 ? (
        <div className="empty">No posts yet. Generate one to get started.</div>
      ) : (
        <>
          <div className="filter-row">
            {FILTERS.map(([key, label]) => {
              const n = key === "all" ? posts.length : posts.filter((p) => p.status === key).length;
              return (
                <button key={key} className={`filter-chip ${filter === key ? "active" : ""}`}
                  onClick={() => setFilter(key)}>
                  {label}{n > 0 ? <span style={{ opacity: 0.7 }}> · {n}</span> : null}
                </button>
              );
            })}
          </div>
          {shown.length === 0 ? (
            <div className="empty">No {filter} posts.</div>
          ) : (
            <div className="masonry">
              {shown.map((p) => <PostCard key={p.id} post={p} onChange={load} />)}
            </div>
          )}
        </>
      )}
    </>
  );
}
