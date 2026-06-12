import { useEffect, useState } from "react";
import { zernioMetrics, getInsights, analyzeViral } from "../api.js";

function renderValue(v) {
  if (typeof v === "string") return <p style={{ margin: "4px 0", lineHeight: 1.5 }}>{v}</p>;
  if (typeof v === "number" || typeof v === "boolean") return <span>{String(v)}</span>;
  if (Array.isArray(v))
    return (
      <ul style={{ margin: "4px 0", paddingLeft: 18 }}>
        {v.map((x, i) => (
          <li key={i} style={{ marginBottom: 4 }}>
            {typeof x === "string" ? x : JSON.stringify(x)}
          </li>
        ))}
      </ul>
    );
  if (v && typeof v === "object")
    return <pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(v, null, 2)}</pre>;
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

function Summary({ s }) {
  const fmt = (n) => (n ?? 0).toLocaleString();
  return (
    <div style={{ marginTop: 10 }}>
      <div className="row" style={{ gap: 10 }}>
        <Stat label="Published posts" value={fmt(s.post_count)} />
        <Stat label="Total impressions" value={fmt(s.impressions)} />
        <Stat label="Total likes" value={fmt(s.total_likes)} />
        <Stat label="Total comments" value={fmt(s.total_comments)} />
        <Stat label="Avg likes/post" value={fmt(s.avg_likes)} />
      </div>
      {s.recent?.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontWeight: 600, color: "var(--mid)", marginBottom: 8 }}>Recent posts</div>
          <div className="pill-list" style={{ maxHeight: 320, overflowY: "auto", paddingRight: 4 }}>
            {s.recent.map((p, i) => (
              <div className="pill" key={i} style={{ alignItems: "flex-start", flexDirection: "column", gap: 4 }}>
                <div style={{ fontSize: 13 }}>{p.content || "(no text)"}{p.content?.length >= 160 ? "…" : ""}</div>
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
  const [viral, setViral] = useState({ post: "", niche: "", impressions: 0, likes: 0, comments: 0, shares: 0 });
  const [viralResult, setViralResult] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const loadZernio = async () => {
    setError("");
    try {
      setZernio(await zernioMetrics());
    } catch (e) {
      setZernio({ ok: false, error: e.message });
    }
  };
  useEffect(() => { loadZernio(); }, []); // eslint-disable-line

  const summary = zernio?.ok ? zernio.summary : null;

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

  const setV = (k, num = true) => (e) =>
    setViral({ ...viral, [k]: num ? Number(e.target.value || 0) : e.target.value });

  const runViral = async () => {
    setError(""); setBusy("viral"); setViralResult(null);
    try {
      if (!viral.post.trim()) throw new Error("Paste the post text first.");
      const res = await analyzeViral(viral);
      setViralResult(res.data);
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  };

  return (
    <>
      {error && <div className="error">{error}</div>}

      <div className="card">
        <h2>Strategy &amp; suggestions</h2>
        <p className="muted">
          The AI reads your LinkedIn metrics (below) and tells you what's working, what isn't,
          and what to do next. No numbers to enter — just set your goal and go.
        </p>
        <div className="row">
          <div style={{ flex: 2 }}>
            <label>Goal</label>
            <input value={goal} onChange={(e) => setGoal(e.target.value)} />
          </div>
          <div style={{ flex: 1 }}>
            <label>Followers <span className="muted">(optional)</span></label>
            <input type="number" min="0" value={followers}
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
        <h2>Analyze a single post</h2>
        <p className="muted">
          Paste any post and its numbers to get a breakdown of <em>why</em> it performed the way it
          did and how to make the next one stronger. (The card above looks at your whole account;
          this one zooms into one post.)
        </p>
        <label>Post text</label>
        <textarea value={viral.post} onChange={setV("post", false)} style={{ minHeight: 100 }} />
        <label>Niche <span className="muted">(optional)</span></label>
        <input value={viral.niche} onChange={setV("niche", false)} placeholder="AI consulting for SMBs" />
        <div className="row">
          {[["impressions", "Impressions"], ["likes", "Likes"], ["comments", "Comments"], ["shares", "Shares"]].map(
            ([k, label]) => (
              <div key={k} style={{ minWidth: 120 }}>
                <label>{label}</label>
                <input type="number" min="0" value={viral[k]} onChange={setV(k)} />
              </div>
            )
          )}
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn-primary" disabled={busy === "viral"} onClick={runViral}>
            {busy === "viral" ? "Analyzing…" : "Analyze post"}
          </button>
        </div>
        {viralResult && <div style={{ marginTop: 14 }}><HubResult data={viralResult} /></div>}
      </div>

      <div className="card">
        <div className="row">
          <h2 style={{ margin: 0 }}>LinkedIn metrics (Zernio)</h2>
          <div className="spacer" />
          <button className="btn-secondary" onClick={loadZernio}>Refresh</button>
        </div>
        {zernio == null ? (
          <div className="muted" style={{ marginTop: 8 }}>Loading…</div>
        ) : summary ? (
          <Summary s={summary} />
        ) : zernio.ok ? (
          <div style={{ marginTop: 8 }}><HubResult data={zernio.data} /></div>
        ) : (
          <div className="muted" style={{ marginTop: 8 }}>
            Couldn’t load Zernio metrics ({zernio.error}). The strategy card still works with your goal.
          </div>
        )}
      </div>
    </>
  );
}
