import { useEffect, useRef, useState } from "react";
import {
  listPosts, syncPosts, publishPost, schedulePost, deletePost, getPostInfographic, updatePost,
} from "../api.js";
import { uploadMedia } from "../api.js";

const MEDIA_REQUIRED = new Set(["instagram", "tiktok", "youtube", "pinterest", "snapchat"]);
const PLATFORM_LABEL = {
  linkedin: "LinkedIn", twitter: "X", instagram: "Instagram", facebook: "Facebook",
  tiktok: "TikTok", youtube: "YouTube", pinterest: "Pinterest", reddit: "Reddit",
  bluesky: "Bluesky", threads: "Threads", googlebusiness: "Google Business",
  telegram: "Telegram", snapchat: "Snapchat", whatsapp: "WhatsApp", discord: "Discord",
};
const STATUS_FILTERS = [
  ["all", "All"], ["draft", "Drafts"], ["scheduled", "Scheduled"],
  ["published", "Published"], ["failed", "Failed"],
];

function PostCard({ post, onChange }) {
  const [when, setWhen] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [mediaUrl, setMediaUrl] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

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
    try { await fn(); onChange(); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const doSchedule = act(async () => {
    if (!when) throw new Error("Pick a date and time.");
    await schedulePost(post.id, new Date(when).toISOString(), "UTC");
  });

  const doUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      const { url } = await uploadMedia(file);
      await updatePost(post.id, { media: [{ type: file.type.startsWith("video") ? "video" : "image", url }] });
      onChange();
    } catch (e) {
      setError(e.message || "Upload failed");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const doAttachUrl = act(async () => {
    if (!mediaUrl.trim()) throw new Error("Paste a URL first.");
    await updatePost(post.id, { media: [{ type: "image", url: mediaUrl.trim() }] });
    setMediaUrl("");
  });

  const published = post.status === "published";
  const scheduled = post.status === "scheduled";
  const editable = !published && !scheduled;

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
          <button className="btn-ghost btn-compact" onClick={viewInfographic}>
            View infographic
          </button>
        )}
        <div className="spacer" />
        {post.platform_post_url && (
          <a href={post.platform_post_url} target="_blank" rel="noreferrer"
            style={{ color: "var(--teal)", fontSize: 13, fontWeight: 600 }}>
            View on {PLATFORM_LABEL[post.platform] || "platform"} ↗
          </a>
        )}
      </div>

      <div className="post-body">{post.body}</div>
      {post.hashtags?.length > 0 && (
        <div className="hashtags">{post.hashtags.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" ")}</div>
      )}
      {post.error && <div className="error" role="alert">{post.error}</div>}
      {error && <div className="error" role="alert">{error}</div>}

      {editable && (MEDIA_REQUIRED.has(post.platform) || hasMedia) && (
        <div style={{ marginTop: 12, padding: "12px 14px", borderRadius: 8,
          background: needsMedia ? "#fff7ed" : "#f6f7fb", border: needsMedia ? "1px solid #fed7aa" : "none" }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            {needsMedia
              ? `${PLATFORM_LABEL[post.platform] || post.platform} needs an image or video to publish`
              : "Media attached"}
          </div>
          {hasMedia && (
            <div className="muted" style={{ fontSize: 12, marginBottom: 8, wordBreak: "break-all" }}>
              {post.media.map((m) => m.url).filter(Boolean).join(", ")}
            </div>
          )}

          {/* Upload file */}
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <input ref={fileRef} type="file" accept="image/*,video/*"
              style={{ display: "none" }} onChange={doUpload} disabled={busy || uploading} />
            <button className="btn-secondary" disabled={busy || uploading}
              onClick={() => fileRef.current?.click()}
              style={{ whiteSpace: "nowrap" }}>
              {uploading ? "Uploading…" : "Upload file"}
            </button>
            <span className="muted" style={{ fontSize: 12 }}>or paste URL</span>
            <input style={{ flex: 1, minWidth: 160 }} placeholder="https://…"
              value={mediaUrl} onChange={(e) => setMediaUrl(e.target.value)} />
            <button className="btn-secondary" disabled={busy || uploading || !mediaUrl.trim()}
              onClick={doAttachUrl}>
              {hasMedia ? "Replace" : "Attach"}
            </button>
          </div>
        </div>
      )}

      {editable && (
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn-primary" disabled={busy || needsMedia} onClick={act(() => publishPost(post.id))}>
            Publish now
          </button>
          <input type="datetime-local" style={{ width: 220 }} value={when}
            onChange={(e) => setWhen(e.target.value)} />
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
          <span className="muted">Scheduled — publishes automatically.</span>
          <div className="spacer" />
          <button className="btn-ghost" disabled={busy} onClick={act(() => deletePost(post.id))}>Cancel</button>
        </div>
      )}
    </div>
  );
}

export default function Posts({ refreshKey, accounts = [] }) {
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [platformFilter, setPlatformFilter] = useState("all");

  // Platforms the user actually has connected accounts for
  const connectedPlatforms = [...new Set(accounts.map((a) => a.platform).filter(Boolean))];

  const load = async () => {
    setError("");
    try { setPosts(await listPosts()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const refresh = async () => {
    setError(""); setSyncing(true);
    try { setPosts(await syncPosts()); }
    catch (e) { setError(e.message); }
    finally { setSyncing(false); setLoading(false); }
  };

  useEffect(() => { load(); }, [refreshKey]); // eslint-disable-line

  if (loading) return <div className="empty">Loading…</div>;

  // "All channels" always shows every post — connectedPlatforms only decides which
  // per-platform tabs exist, it must never hide posts from the default/all view.
  const channelPosts = platformFilter === "all"
    ? posts
    : posts.filter((p) => p.platform === platformFilter);

  // Then filter by status
  const shown = statusFilter === "all"
    ? channelPosts
    : channelPosts.filter((p) => p.status === statusFilter);

  return (
    <>
      {error && <div className="error" role="alert">{error}</div>}
      <div className="row" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0, color: "var(--blue)" }}>Your posts</h2>
        <div className="spacer" />
        <button className="btn-secondary" disabled={syncing} onClick={refresh}>
          {syncing ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {/* Platform (channel) tabs — only connected platforms */}
      {connectedPlatforms.length > 1 && (
        <div className="filter-row" style={{ marginBottom: 8 }}>
          <button className={`filter-chip ${platformFilter === "all" ? "active" : ""}`}
            onClick={() => setPlatformFilter("all")}>
            All channels
          </button>
          {connectedPlatforms.map((p) => (
            <button key={p} className={`filter-chip ${platformFilter === p ? "active" : ""}`}
              onClick={() => setPlatformFilter(p)}>
              {PLATFORM_LABEL[p] || p}
              {(() => { const n = posts.filter((x) => x.platform === p).length; return n > 0 ? <span style={{ opacity: 0.6 }}> · {n}</span> : null; })()}
            </button>
          ))}
        </div>
      )}

      {/* Status filters */}
      {channelPosts.length > 0 && (
        <div className="filter-row" style={{ marginBottom: 16 }}>
          {STATUS_FILTERS.map(([key, label]) => {
            const n = key === "all" ? channelPosts.length : channelPosts.filter((p) => p.status === key).length;
            return (
              <button key={key} className={`filter-chip ${statusFilter === key ? "active" : ""}`}
                onClick={() => setStatusFilter(key)}>
                {label}{n > 0 ? <span style={{ opacity: 0.7 }}> · {n}</span> : null}
              </button>
            );
          })}
        </div>
      )}

      <div aria-live="polite">
        {posts.length === 0 ? (
          <div className="empty">No posts yet. Generate one to get started.</div>
        ) : channelPosts.length === 0 ? (
          <div className="empty">No posts for your connected channels yet.</div>
        ) : shown.length === 0 ? (
          <div className="empty">No {statusFilter} posts.</div>
        ) : (
          <div className="masonry">
            {shown.map((p) => <PostCard key={p.id} post={p} onChange={load} />)}
          </div>
        )}
      </div>
    </>
  );
}
