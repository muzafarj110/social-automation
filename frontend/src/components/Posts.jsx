import { useEffect, useState } from "react";
import { listPosts, publishPost, schedulePost, deletePost } from "../api.js";

function PostCard({ post, onChange }) {
  const [when, setWhen] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

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

  const done = post.status === "published";

  return (
    <div className="card">
      <div className="row">
        <span className={`badge ${post.status}`}>{post.status}</span>
        {post.scheduled_for && (
          <span className="muted">for {new Date(post.scheduled_for).toLocaleString()}</span>
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
      {post.hashtags?.length > 0 && <div className="hashtags">{post.hashtags.join("  ")}</div>}
      {post.error && <div className="error">{post.error}</div>}
      {error && <div className="error">{error}</div>}

      {!done && (
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn-primary" disabled={busy} onClick={act(() => publishPost(post.id))}>
            Publish now
          </button>
          <input
            type="datetime-local"
            style={{ width: 220 }}
            value={when}
            onChange={(e) => setWhen(e.target.value)}
          />
          <button className="btn-secondary" disabled={busy} onClick={doSchedule}>
            Schedule
          </button>
          <div className="spacer" />
          <button className="btn-ghost" disabled={busy} onClick={act(() => deletePost(post.id))}>
            Delete
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

  useEffect(() => {
    load();
  }, [refreshKey]); // eslint-disable-line

  if (loading) return <div className="empty">Loading…</div>;

  return (
    <>
      {error && <div className="error">{error}</div>}
      <div className="row" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0, color: "var(--blue)" }}>Your posts</h2>
        <div className="spacer" />
        <button className="btn-secondary" onClick={load}>
          Refresh
        </button>
      </div>
      {posts.length === 0 ? (
        <div className="empty">No posts yet. Generate one to get started.</div>
      ) : (
        posts.map((p) => <PostCard key={p.id} post={p} onChange={load} />)
      )}
    </>
  );
}
