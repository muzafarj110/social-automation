import { useEffect, useState } from "react";
import { zernioMetrics, getInsights } from "../api.js";
import { platformLabel } from "../utils/platforms.js";
import { aggregatePosts, filterPostsByPlatform } from "../utils/analyticsAggregate.js";

function objText(o) {
  return Object.entries(o)
    .filter(([k]) => !k.startsWith("_"))
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v && typeof v === "object" ? JSON.stringify(v) : v}`)
    .join(" — ");
}

function renderValue(v) {
  if (typeof v === "string") return <p style={{ margin: "4px 0", lineHeight: 1.5 }}>{v}</p>;
  if (typeof v === "number" || typeof v === "boolean") return <span>{String(v)}</span>;
  if (Array.isArray(v))
    return (
      <ul style={{ margin: "4px 0", paddingLeft: 18 }}>
        {v.map((x, i) => (
          <li key={i} style={{ marginBottom: 4 }}>
            {x && typeof x === "object" ? objText(x) : String(x)}
          </li>
        ))}
      </ul>
    );
  if (v && typeof v === "object")
    return (
      <div>
        {Object.entries(v).filter(([k]) => !k.startsWith("_")).map(([k, vv]) => (
          <div key={k} style={{ fontSize: 13, marginBottom: 2 }}>
            <span style={{ fontWeight: 600, color: "var(--mid)" }}>{k.replace(/_/g, " ")}: </span>
            {vv && typeof vv === "object" ? objText(vv) : String(vv)}
          </div>
        ))}
      </div>
    );
  return <span>{String(v)}</span>;
}

function HubResult({ data }) {
  if (!data) return null;
  const entries = Object.entries(data).filter(([k]) => !k.startsWith("_"));
  if (!entries.length) return <div className="muted">No details returned.</div>;
  return (
    <div>
      {entries.map(([k, v]) => (
        <div key={k} style={{ marginBottom: 10 }}>
          <div style={{ fontWeight: 600, color: "var(--mid)", textTransform: "capitalize" }}>
            {k.replace(/_/g, " ")}
          </div>
          {renderValue(v)}
        </div>
      ))}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div style={{
      background: "var(--light)", borderRadius: "var(--radius)", padding: "12px 16px",
      minWidth: 110, flex: "1 0 auto",
    }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: "var(--blue)" }}>{value}</div>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
    </div>
  );
}

function PlatformBadge({ platform }) {
  if (!platform) return null;
  return <span className="badge kind" style={{ flexShrink: 0 }}>{platformLabel(platform)}</span>;
}

function Summary({ s, showPlatformBadges }) {
  const top = (s.recent || [])
    .slice()
    .sort((a, b) => (b.impressions || 0) - (a.impressions || 0))
    .slice(0, 6);
  const maxImp = Math.max(1, ...top.map((p) => p.impressions || 0));

  return (
    <div style={{ marginTop: 10 }}>
      {top.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 600, color: "var(--mid)", marginBottom: 4 }}>Top posts by impressions</div>
          <div className="bars">
            {top.map((p, i) => (
              <div className="bar-row" key={i}>
                {showPlatformBadges && <PlatformBadge platform={p.platform} />}
                <span className="bar-label">{(p.content || "(no text)").slice(0, 44)}</span>
                <span className="bar-track">
                  <span className="bar-fill" style={{ width: `${Math.round(((p.impressions || 0) / maxImp) * 100)}%` }} />
                </span>
                <span className="bar-val">{(p.impressions || 0).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {s.recent?.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontWeight: 600, color: "var(--mid)", marginBottom: 2 }}>Recent posts</div>
          <p className="muted" style={{ fontSize: 12, margin: "0 0 8px" }}>
            Pulled live from the account itself — includes anything posted there, not just posts made in Autopilot.
          </p>
          <div className="pill-list" style={{ maxHeight: 320, overflowY: "auto", paddingRight: 4 }}>
            {s.recent.map((p, i) => (
              <div className="pill" key={i} style={{ alignItems: "flex-start", flexDirection: "column", gap: 4 }}>
                <div className="row" style={{ gap: 8, width: "100%" }}>
                  {showPlatformBadges && <PlatformBadge platform={p.platform} />}
                  <div style={{ fontSize: 13 }}>{p.content || "(no text)"}{p.content?.length >= 160 ? "…" : ""}</div>
                </div>
                <div className="row" style={{ gap: 10, width: "100%" }}>
                  <span className="muted" style={{ fontSize: 12 }}>
                    {p.impressions} impressions · {p.likes} likes · {p.comments} comments
                  </span>
                  <div className="spacer" />
                  {p.url && (
                    <a href={p.url} target="_blank" rel="noreferrer"
                       style={{ color: "var(--teal)", fontSize: 12, fontWeight: 600 }}>View ↗</a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Analytics() {
  const [zernio, setZernio] = useState(null);
  const [goal, setGoal] = useState("grow followers and generate leads");
  const [followers, setFollowers] = useState("");
  const [insights, setInsights] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [platformFilter, setPlatformFilter] = useState("all");

  const loadZernio = async () => {
    setError("");
    setRefreshing(true);
    try {
      setZernio(await zernioMetrics());
      setLastRefreshed(new Date());
    } catch (e) {
      setZernio({ ok: false, error: e.message });
    } finally {
      setRefreshing(false);
    }
  };
  useEffect(() => { loadZernio(); }, []); // eslint-disable-line

  // `platforms` is every account connected (from the DB), even ones Zernio
  // returned no posts for; `summary` is always the all-platforms merged total.
  const platforms = zernio?.ok ? (zernio.platforms || []) : [];
  const rawPosts = zernio?.ok ? (zernio.data?.posts || []) : [];
  const allSummary = zernio?.ok ? zernio.summary : null;
  const summary = !zernio?.ok || platformFilter === "all"
    ? allSummary
    : aggregatePosts(filterPostsByPlatform(rawPosts, platformFilter));

  const runInsights = async () => {
    setError(""); setBusy("insights"); setInsights(null);
    try {
      const s = summary || {};
      const res = await getInsights({
        followers: Number(followers || 0),
        impressions: s.impressions || 0,
        profile_views: 0,
        post_count: s.post_count || 0,
        avg_likes: s.avg_likes || 0,
        avg_comments: s.avg_comments || 0,
        avg_shares: s.avg_shares || 0,
        timeframe: "Last 30 days",
        goal: goal || null,
      });
      setInsights(res.data);
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  };

  return (
    <>
      {error && <div className="error" role="alert">{error}</div>}

      {platforms.length > 1 && (
        <div className="row" style={{ gap: 6, flexWrap: "wrap", marginBottom: 14 }} role="tablist" aria-label="Filter analytics by account">
          <button
            type="button" role="tab" aria-selected={platformFilter === "all"}
            className={`filter-chip ${platformFilter === "all" ? "active" : ""}`}
            onClick={() => setPlatformFilter("all")}
          >
            All accounts
          </button>
          {platforms.map((p) => (
            <button
              key={p} type="button" role="tab" aria-selected={platformFilter === p}
              className={`filter-chip ${platformFilter === p ? "active" : ""}`}
              onClick={() => setPlatformFilter(p)}
            >
              {platformLabel(p)}
            </button>
          ))}
        </div>
      )}

      {summary && (
        <div className="kpi-strip">
          <div className="kpi-tile"><div className="v">{(summary.post_count ?? 0).toLocaleString()}</div><div className="l">Published posts</div></div>
          <div className="kpi-tile"><div className="v">{(summary.impressions ?? 0).toLocaleString()}</div><div className="l">Impressions</div></div>
          <div className="kpi-tile"><div className="v">{(summary.total_likes ?? 0).toLocaleString()}</div><div className="l">Total likes</div></div>
          <div className="kpi-tile"><div className="v">{(summary.total_comments ?? 0).toLocaleString()}</div><div className="l">Comments</div></div>
          <div className="kpi-tile"><div className="v">{(summary.avg_likes ?? 0).toLocaleString()}</div><div className="l">Avg likes/post</div></div>
        </div>
      )}

      <div className="masonry">
      <div className="card">
        <h2>Strategy &amp; suggestions</h2>
        <p className="muted">
          The AI reads your connected accounts' metrics (below) and tells you what's working, what isn't,
          and what to do next. No numbers to enter — just set your goal and go.
        </p>
        <div className="row">
          <div style={{ flex: 2 }}>
            <label htmlFor="an-goal">Goal</label>
            <input id="an-goal" value={goal} onChange={(e) => setGoal(e.target.value)} />
          </div>
          <div style={{ flex: 1 }}>
            <label htmlFor="an-followers">Followers <span className="muted">(optional)</span></label>
            <input id="an-followers" type="number" min="0" value={followers}
              onChange={(e) => setFollowers(e.target.value)} placeholder="e.g. 1200" />
          </div>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn-primary" disabled={busy === "insights"} onClick={runInsights}>
            {busy === "insights" ? "Analyzing…" : "Get strategy & suggestions"}
          </button>
          {summary && (
            <span className="muted" style={{ alignSelf: "center" }}>
              Using {summary.post_count} posts · {(summary.impressions || 0).toLocaleString()} impressions
            </span>
          )}
        </div>
        {insights && <div style={{ marginTop: 14 }}><HubResult data={insights} /></div>}
      </div>

      <div className="card">
        <div className="row">
          <h2 style={{ margin: 0 }}>Reach &amp; engagement</h2>
          <div className="spacer" />
          {lastRefreshed && (
            <span className="muted" style={{ fontSize: 12 }}>
              {refreshing ? "Refreshing…" : `Updated ${lastRefreshed.toLocaleTimeString()}`}
            </span>
          )}
          <button className="btn-secondary" onClick={loadZernio} disabled={refreshing}>
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
        <div aria-live="polite">
          {zernio == null ? (
            <div className="muted" style={{ marginTop: 8 }}>Loading…</div>
          ) : summary ? (
            <Summary s={summary} showPlatformBadges={platformFilter === "all" && platforms.length > 1} />
          ) : zernio.ok ? (
            <div style={{ marginTop: 8 }}><HubResult data={zernio.data} /></div>
          ) : (
            <div className="empty" style={{ marginTop: 8 }}>
              No performance data yet. Connect a social account and publish a few posts —
              your reach and engagement will show up here automatically.
            </div>
          )}
        </div>
      </div>
      </div>
    </>
  );
}
