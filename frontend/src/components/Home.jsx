import { useEffect, useState } from "react";
import { listPosts, listInbox, listCampaigns, zernioMetrics } from "../api.js";

function Tile({ label, value }) {
  return (
    <div style={{
      background: "var(--light)", borderRadius: "var(--radius)", padding: "14px 18px",
      minWidth: 120, flex: "1 0 auto", textAlign: "center",
    }}>
      <div style={{ fontSize: 26, fontWeight: 700, color: "var(--blue)" }}>{value}</div>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
    </div>
  );
}

export default function Home({ goTab }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [posts, inbox, campaigns] = await Promise.all([
          listPosts().catch(() => []),
          listInbox("pending").catch(() => []),
          listCampaigns().catch(() => []),
        ]);
        let metrics = null;
        try { const z = await zernioMetrics(); if (z.ok) metrics = z.summary; } catch { /* no key */ }
        setData({ posts, inbox, campaigns, metrics });
      } catch (e) { setError(e.message); }
    })();
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <div className="empty">Loading…</div>;

  const weekAgo = new Date(Date.now() - 7 * 864e5);
  const publishedThisWeek = data.posts.filter(
    (p) => p.status === "published" && new Date(p.updated_at) >= weekAgo
  ).length;
  const scheduled = data.posts
    .filter((p) => p.status === "scheduled")
    .sort((a, b) => new Date(a.scheduled_for) - new Date(b.scheduled_for));
  const drafts = data.posts.filter((p) => p.status === "draft").length;
  const activeCampaigns = data.campaigns.filter((c) => c.status === "active");

  return (
    <>
      <div className="card">
        <h2>This week at a glance</h2>
        <div className="row" style={{ gap: 10 }}>
          <Tile label="Published (7d)" value={publishedThisWeek} />
          <Tile label="Scheduled" value={scheduled.length} />
          <Tile label="Drafts" value={drafts} />
          <Tile label="Awaiting approval" value={data.inbox.length} />
          <Tile label="Active campaigns" value={activeCampaigns.length} />
        </div>
      </div>

      <div className="card">
        <div className="row">
          <h2 style={{ margin: 0 }}>Coming up</h2>
          <div className="spacer" />
          <button className="btn-secondary" onClick={() => goTab("posts")}>All posts</button>
        </div>
        {scheduled.length === 0 ? (
          <div className="empty">Nothing scheduled yet. Set up an Autopilot campaign to fill your queue.</div>
        ) : (
          <div className="pill-list" style={{ marginTop: 8 }}>
            {scheduled.slice(0, 5).map((p) => (
              <div className="pill" key={p.id} style={{ flexDirection: "column", alignItems: "flex-start", gap: 4 }}>
                <span className="muted" style={{ fontSize: 12 }}>
                  {new Date(p.scheduled_for).toLocaleString()}
                </span>
                <span style={{ fontSize: 13 }}>{p.body.slice(0, 140)}{p.body.length > 140 ? "…" : ""}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h2>Needs your review</h2>
        <div className="pill-list" style={{ marginTop: 8 }}>
          <div className="pill">
            <span><strong>{data.inbox.length}</strong> inbox item{data.inbox.length === 1 ? "" : "s"} awaiting approval</span>
            <div className="spacer" />
            <button className="btn-secondary" onClick={() => goTab("inbox")}>Open Inbox</button>
          </div>
          <div className="pill">
            <span><strong>{drafts}</strong> draft{drafts === 1 ? "" : "s"} ready to publish or schedule</span>
            <div className="spacer" />
            <button className="btn-secondary" onClick={() => goTab("posts")}>Open Posts</button>
          </div>
        </div>
      </div>

      {data.metrics && (
        <div className="card">
          <div className="row">
            <h2 style={{ margin: 0 }}>Performance</h2>
            <div className="spacer" />
            <button className="btn-secondary" onClick={() => goTab("analytics")}>Analytics</button>
          </div>
          <div className="row" style={{ gap: 10, marginTop: 8 }}>
            <Tile label="Posts" value={(data.metrics.post_count || 0).toLocaleString()} />
            <Tile label="Impressions" value={(data.metrics.impressions || 0).toLocaleString()} />
            <Tile label="Total likes" value={(data.metrics.total_likes || 0).toLocaleString()} />
            <Tile label="Avg likes/post" value={(data.metrics.avg_likes || 0).toLocaleString()} />
          </div>
        </div>
      )}
    </>
  );
}
