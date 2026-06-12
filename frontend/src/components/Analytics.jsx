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

const METRIC_FIELDS = [
  ["followers", "Followers"],
  ["impressions", "Impressions"],
  ["profile_views", "Profile views"],
  ["post_count", "Posts"],
  ["avg_likes", "Avg likes"],
  ["avg_comments", "Avg comments"],
  ["avg_shares", "Avg shares"],
];

export default function Analytics() {
  const [zernio, setZernio] = useState(null);
  const [metrics, setMetrics] = useState({
    followers: 0, impressions: 0, profile_views: 0, post_count: 0,
    avg_likes: 0, avg_comments: 0, avg_shares: 0,
    timeframe: "Last 30 days", goal: "grow followers and generate leads",
  });
  const [insights, setInsights] = useState(null);
  const [viral, setViral] = useState({ post: "", niche: "", impressions: 0, likes: 0, comments: 0, shares: 0 });
  const [viralResult, setViralResult] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const loadZernio = async () => {
    setError("");
    try {
      const res = await zernioMetrics();
      setZernio(res);
    } catch (e) {
      setZernio({ ok: false, error: e.message });
    }
  };
  useEffect(() => { loadZernio(); }, []); // eslint-disable-line

  const setM = (k, num = true) => (e) =>
    setMetrics({ ...metrics, [k]: num ? Number(e.target.value || 0) : e.target.value });
  const setV = (k, num = true) => (e) =>
    setViral({ ...viral, [k]: num ? Number(e.target.value || 0) : e.target.value });

  const runInsights = async () => {
    setError(""); setBusy("insights"); setInsights(null);
    try {
      const res = await getInsights(metrics);
      setInsights(res.data);
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  };

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
        <div className="row">
          <h2 style={{ margin: 0 }}>LinkedIn metrics (Zernio)</h2>
          <div className="spacer" />
          <button className="btn-secondary" onClick={loadZernio}>Refresh</button>
        </div>
        {zernio == null ? (
          <div className="muted" style={{ marginTop: 8 }}>Loading…</div>
        ) : zernio.ok ? (
          <div style={{ marginTop: 8 }}><HubResult data={zernio.data} /></div>
        ) : (
          <div className="muted" style={{ marginTop: 8 }}>
            Couldn’t load Zernio metrics ({zernio.error}). You can still enter your numbers below for AI insights.
          </div>
        )}
      </div>

      <div className="card">
        <h2>AI insights</h2>
        <p className="muted">Enter your current numbers — the Hub’s analytics model interprets them and recommends what to do next.</p>
        <div className="row">
          {METRIC_FIELDS.map(([k, label]) => (
            <div key={k} style={{ minWidth: 120 }}>
              <label>{label}</label>
              <input type="number" min="0" value={metrics[k]} onChange={setM(k)} />
            </div>
          ))}
        </div>
        <label>Goal</label>
        <input value={metrics.goal} onChange={setM("goal", false)} />
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn-primary" disabled={busy === "insights"} onClick={runInsights}>
            {busy === "insights" ? "Analyzing…" : "Get AI insights"}
          </button>
        </div>
        {insights && <div style={{ marginTop: 14 }}><HubResult data={insights} /></div>}
      </div>

      <div className="card">
        <h2>Analyze a post</h2>
        <p className="muted">Paste a post and its numbers to see why it did (or didn’t) perform.</p>
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
    </>
  );
}
