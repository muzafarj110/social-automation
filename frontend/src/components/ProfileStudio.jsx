import { useState } from "react";
import {
  profileOptimize,
  profileHeadlines,
  profileFeatured,
  profileRecommendation,
} from "../api.js";

function objText(o) {
  return Object.entries(o)
    .filter(([k]) => !k.startsWith("_"))
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v && typeof v === "object" ? JSON.stringify(v) : v}`)
    .join(" — ");
}
function renderVal(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === "string") return <p style={{ margin: "2px 0", lineHeight: 1.5, fontSize: 13 }}>{v}</p>;
  if (typeof v === "number" || typeof v === "boolean") return <span style={{ fontSize: 13 }}>{String(v)}</span>;
  if (Array.isArray(v))
    return (
      <ul style={{ margin: "2px 0", paddingLeft: 18, fontSize: 13 }}>
        {v.map((x, i) => <li key={i} style={{ marginBottom: 4 }}>{x && typeof x === "object" ? objText(x) : String(x)}</li>)}
      </ul>
    );
  if (typeof v === "object")
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
function HubBlocks({ data }) {
  if (!data) return null;
  const entries = Object.entries(data).filter(([k]) => !k.startsWith("_"));
  if (!entries.length) return <div className="muted">No details.</div>;
  return (
    <div>
      {entries.map(([k, v]) => (
        <div key={k} style={{ marginBottom: 8 }}>
          <div style={{ fontWeight: 600, color: "var(--mid)", textTransform: "capitalize", fontSize: 13 }}>
            {k.replace(/_/g, " ")}
          </div>
          {renderVal(v)}
        </div>
      ))}
    </div>
  );
}

const TOOLS = {
  optimize: {
    label: "Optimize profile", fn: profileOptimize,
    blurb: "Rewrite your headline and About section for impact.",
    fields: [
      { name: "current_headline", label: "Current headline", req: true },
      { name: "current_summary", label: "Current About / summary", req: true, area: true },
      { name: "role", label: "Your role", req: true },
      { name: "industry", label: "Industry", req: true },
      { name: "goals", label: "Goals" },
    ],
  },
  headlines: {
    label: "Headline ideas", fn: profileHeadlines,
    blurb: "Get A/B headline variants tuned to your goal.",
    fields: [
      { name: "current_headline", label: "Current headline", req: true },
      { name: "role", label: "Your role", req: true },
      { name: "industry", label: "Industry" },
      { name: "goal", label: "Goal" },
      { name: "keywords", label: "Keywords to include" },
    ],
  },
  featured: {
    label: "Featured section", fn: profileFeatured,
    blurb: "Ideas for what to pin to your Featured section.",
    fields: [
      { name: "role", label: "Your role", req: true },
      { name: "industry", label: "Industry" },
      { name: "goal", label: "Goal" },
      { name: "current_featured", label: "Currently featured", area: true },
      { name: "links_available", label: "Links you can feature" },
    ],
  },
  recommendation: {
    label: "Recommendation", fn: profileRecommendation,
    blurb: "Draft a recommendation for a colleague.",
    fields: [
      { name: "person_name", label: "Person's name", req: true },
      { name: "person_role", label: "Their role", req: true },
      { name: "your_role", label: "Your role", req: true },
      { name: "relationship", label: "How you worked together", req: true },
      { name: "key_achievement", label: "A key achievement", req: true, area: true },
      { name: "key_quality", label: "A standout quality", req: true },
      { name: "tone", label: "Tone" },
    ],
  },
};

export default function ProfileStudio() {
  const [tool, setTool] = useState("optimize");
  const [form, setForm] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const cfg = TOOLS[tool];
  const pick = (t) => { setTool(t); setForm({}); setResult(null); setError(""); };
  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value });

  const run = async (e) => {
    e.preventDefault();
    setError(""); setBusy(true); setResult(null);
    try {
      for (const f of cfg.fields) {
        if (f.req && !(form[f.name] || "").trim()) throw new Error(`${f.label} is required.`);
      }
      const payload = Object.fromEntries(
        Object.entries(form).filter(([, v]) => v && String(v).trim())
      );
      const res = await cfg.fn(payload);
      setResult(res.data);
    } catch (e2) { setError(e2.message); }
    finally { setBusy(false); }
  };

  return (
    <>
      <div className="row" style={{ marginBottom: 16, flexWrap: "wrap" }}>
        {Object.entries(TOOLS).map(([id, t]) => (
          <button key={id} className={tool === id ? "btn-primary" : "btn-secondary"} onClick={() => pick(id)}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="card">
        <h2>{cfg.label}</h2>
        <p className="muted">{cfg.blurb}</p>
        <form onSubmit={run}>
          <div className="grid-2">
            {cfg.fields.map((f) => (
              <div key={f.name} style={f.area ? { gridColumn: "1 / -1" } : undefined}>
                <label>
                  {f.label} {f.req ? <span style={{ color: "var(--teal)" }}>*</span> : <span className="muted">(optional)</span>}
                </label>
                {f.area
                  ? <textarea value={form[f.name] || ""} onChange={set(f.name)} style={{ minHeight: 90 }} />
                  : <input value={form[f.name] || ""} onChange={set(f.name)} />}
              </div>
            ))}
          </div>
          {error && <div className="flash error">{error}</div>}
          <div className="row" style={{ marginTop: 14 }}>
            <button className="btn-primary" type="submit" disabled={busy}>
              {busy ? "Generating…" : "Generate"}
            </button>
          </div>
        </form>
      </div>

      {result && (
        <div className="card">
          <h2>Result</h2>
          <HubBlocks data={result} />
        </div>
      )}
    </>
  );
}
