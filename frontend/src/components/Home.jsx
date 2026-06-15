import { useEffect, useState } from "react";
import { listPosts, listInbox, listCampaigns, zernioMetrics, listAccounts, getBrand } from "../api.js";

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

const PROFILE_LEAD = {
  individual: "Let's get you posting consistently — mostly hands-off.",
  influencer: "Let's build your content engine across platforms.",
  startup: "Let's turn your brand into a lead-generating machine.",
  company: "Let's set up your brand workspace.",
};

export default function Home({ goTab, user }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [posts, inbox, campaigns, accounts, brand] = await Promise.all([
          listPosts().catch(() => []),
          listInbox("pending").catch(() => []),
          listCampaigns().catch(() => []),
          listAccounts().catch(() => []),
          getBrand().catch(() => ({})),
        ]);
        let metrics = null;
        try { const z = await zernioMetrics(); if (z.ok) metrics = z.summary; } catch { /* no key */ }
        setData({ posts, inbox, campaigns, accounts, brand, metrics });
      } catch (e) { setError(e.message); }
    })();
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <div className="empty">Loading…</div>;

  const weekAgo = new Date(Date.now() - 7 * 864e5);
  const publishedThisWeek = data.posts.filter((p) => p.status === "published" && new Date(p.updated_at) >= weekAgo).length;
  const scheduled = data.posts.filter((p) => p.status === "scheduled").sort((a, b) => new Date(a.scheduled_for) - new Date(b.scheduled_for));
  const drafts = data.posts.filter((p) => p.status === "draft").length;
  const activeCampaigns = data.campaigns.filter((c) => c.status === "active");

  const connected = data.accounts.length > 0;
  const brandReady = !!(data.brand && (data.brand.voice || data.brand.brand_name));
  const hasCampaign = data.campaigns.length > 0;
  const steps = [
    { done: connected, title: "Connect your channels", desc: "Connect your channels and link a social account.", tab: "accounts", cta: "Connect" },
    { done: brandReady, title: "Define your brand", desc: "Set your voice, audience and positioning so every post is on-brand.", tab: "strategy", cta: "Set up brand" },
    { done: hasCampaign, title: "Launch autopilot", desc: "Create a campaign that generates and schedules posts for you.", tab: "campaigns", cta: "Create campaign" },
  ];
  const setupDone = steps.every((s) => s.done);
  const lead = PROFILE_LEAD[user?.profile_type] || "A few steps to put your marketing on autopilot.";

  return (
    <>
      <div className="kpi-strip">
        <div className="kpi-tile"><div className="v">{publishedThisWeek}</div><div className="l">Published (7d)</div></div>
        <div className="kpi-tile"><div className="v">{scheduled.length}</div><div className="l">Scheduled</div></div>
        <div className="kpi-tile"><div className="v">{drafts}</div><div className="l">Drafts</div></div>
        <div className="kpi-tile"><div className="v">{data.inbox.length}</div><div className="l">Awaiting approval</div></div>
        <div className="kpi-tile"><div className="v">{activeCampaigns.length}</div><div className="l">Active campaigns</div></div>
      </div>

      <div className="masonry">
      {!setupDone && (
        <div className="card">
          <h2>Get set up</h2>
          <p className="muted" style={{ marginTop: -6 }}>{lead}</p>
          <div className="pill-list" style={{ marginTop: 10 }}>
            {steps.map((s, i) => (
              <div className="pill" key={i} style={{ alignItems: "center" }}>
                <span style={{
                  width: 24, height: 24, borderRadius: "50%", display: "grid", placeItems: "center",
                  fontSize: 13, fontWeight: 700, flexShrink: 0,
                  background: s.done ? "#dcfce7" : "var(--light)", color: s.done ? "#166534" : "var(--mid)",
                }}>{s.done ? "✓" : i + 1}</span>
                <div>
                  <div style={{ fontWeight: 600, color: "var(--ink)" }}>{s.title}</div>
                  <div className="muted" style={{ fontSize: 13 }}>{s.desc}</div>
                </div>
                <div className="spacer" />
                {s.done
                  ? <span className="badge published">Done</span>
                  : <button className="btn-primary" onClick={() => goTab(s.tab)}>{s.cta}</button>}
              </div>
            ))}
          </div>
        </div>
      )}

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

      <div className="card">
        <div className="row">
          <h2 style={{ margin: 0 }}>Coming up</h2>
          <div className="spacer" />
          <button className="btn-secondary" onClick={() => goTab("posts")}>All posts</button>
        </div>
        {scheduled.length === 0 ? (
          <div className="empty">Nothing scheduled yet. {hasCampaign ? "Your autopilot will fill this." : "Set up an Autopilot campaign to fill your queue."}</div>
        ) : (
          <div className="pill-list" style={{ marginTop: 8 }}>
            {scheduled.slice(0, 5).map((p) => (
              <div className="pill" key={p.id} style={{ flexDirection: "column", alignItems: "flex-start", gap: 4 }}>
                <span className="muted" style={{ fontSize: 12 }}>{new Date(p.scheduled_for).toLocaleString()}</span>
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
      </div>
    </>
  );
}
