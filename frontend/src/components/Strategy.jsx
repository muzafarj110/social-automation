import { useEffect, useState } from "react";
import { getBrand, saveBrand, brandGenerate } from "../api.js";

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
  brand_voice: {
    label: "Brand voice", blurb: "Analyze a few samples to define your voice.",
    fields: [{ name: "content_samples", label: "Paste 2–3 samples of your writing", req: true, area: true },
             { name: "industry", label: "Industry" }],
  },
  customer_persona: {
    label: "Customer persona", blurb: "Build your ideal-customer profile.",
    fields: [{ name: "product", label: "Your product/service", req: true },
             { name: "market", label: "Market" },
             { name: "pain_points", label: "Known pain points", area: true }],
  },
  uvp: {
    label: "Positioning (UVP)", blurb: "Craft your unique value proposition.",
    fields: [{ name: "product", label: "Your product/service", req: true },
             { name: "audience", label: "Audience" },
             { name: "competitors", label: "Competitors" },
             { name: "key_benefit", label: "Key benefit" }],
  },
  competitor_analysis: {
    label: "Competitor analysis", blurb: "Size up the landscape.",
    fields: [{ name: "topic", label: "Topic / niche", req: true },
             { name: "depth", label: "Depth (quick / deep)" },
             { name: "focus", label: "Focus" }],
  },
  content_strategy: {
    label: "Content strategy", blurb: "A themed plan for the weeks ahead.",
    fields: [{ name: "topic", label: "Topic / niche", req: true },
             { name: "audience", label: "Audience" },
             { name: "keywords", label: "Keywords" },
             { name: "timeframe", label: "Timeframe (e.g. 4 weeks)" }],
  },
};

const PROFILE_FIELDS = [
  ["brand_name", "Brand name", false],
  ["industry", "Industry", false],
  ["audience", "Target audience", false],
  ["voice", "Brand voice / tone", true],
  ["mission", "Mission", true],
  ["positioning", "Positioning (UVP)", true],
];

export default function Strategy() {
  const [profile, setProfile] = useState({});
  const [loaded, setLoaded] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");
  const [error, setError] = useState("");

  const [tool, setTool] = useState("brand_voice");
  const [toolForm, setToolForm] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getBrand().then((b) => { setProfile(b || {}); setLoaded(true); }).catch((e) => { setError(e.message); setLoaded(true); });
  }, []);

  const setP = (k) => (e) => setProfile({ ...profile, [k]: e.target.value });

  const save = async () => {
    setError(""); setSavedMsg(""); setBusy(true);
    try {
      await saveBrand({
        brand_name: profile.brand_name || null, industry: profile.industry || null,
        audience: profile.audience || null, voice: profile.voice || null,
        mission: profile.mission || null, positioning: profile.positioning || null,
      });
      setSavedMsg("Brand profile saved. New content will use this voice & audience.");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const cfg = TOOLS[tool];
  const pickTool = (t) => { setTool(t); setToolForm({}); setResult(null); setError(""); };
  const setT = (name) => (e) => setToolForm({ ...toolForm, [name]: e.target.value });

  const runTool = async (e) => {
    e.preventDefault();
    setError(""); setBusy(true); setResult(null);
    try {
      for (const f of cfg.fields) if (f.req && !(toolForm[f.name] || "").trim()) throw new Error(`${f.label} is required.`);
      const params = Object.fromEntries(Object.entries(toolForm).filter(([, v]) => v && String(v).trim()));
      const res = await brandGenerate(tool, params);
      setResult(res.data);
    } catch (e2) { setError(e2.message); }
    finally { setBusy(false); }
  };

  const saveToLibrary = async () => {
    setSavedMsg(""); setError("");
    try {
      await saveBrand({ docs: { [tool]: result } });
      setSavedMsg(`Saved "${cfg.label}" to your brand library.`);
    } catch (e) { setError(e.message); }
  };

  if (!loaded) return <div className="empty">Loading…</div>;

  return (
    <>
      {error && <div className="error">{error}</div>}
      {savedMsg && <div className="success">{savedMsg}</div>}

      <div className="card">
        <h2>Your brand</h2>
        <p className="muted">This is your marketing brain — every campaign and post uses your voice and audience.</p>
        {PROFILE_FIELDS.map(([k, label, area]) => (
          <div key={k}>
            <label>{label}</label>
            {area
              ? <textarea value={profile[k] || ""} onChange={setP(k)} style={{ minHeight: 70 }} />
              : <input value={profile[k] || ""} onChange={setP(k)} />}
          </div>
        ))}
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn-primary" disabled={busy} onClick={save}>Save brand profile</button>
        </div>
      </div>

      <div className="card">
        <h2>Build it with AI</h2>
        <div className="row" style={{ flexWrap: "wrap" }}>
          {Object.entries(TOOLS).map(([id, t]) => (
            <button key={id} className={tool === id ? "btn-primary" : "btn-secondary"} onClick={() => pickTool(id)}>
              {t.label}
            </button>
          ))}
        </div>
        <p className="muted" style={{ marginTop: 8 }}>{cfg.blurb}</p>
        <form onSubmit={runTool}>
          {cfg.fields.map((f) => (
            <div key={f.name}>
              <label>{f.label} {f.req ? <span style={{ color: "var(--teal)" }}>*</span> : <span className="muted">(optional)</span>}</label>
              {f.area
                ? <textarea value={toolForm[f.name] || ""} onChange={setT(f.name)} style={{ minHeight: 80 }} />
                : <input value={toolForm[f.name] || ""} onChange={setT(f.name)} />}
            </div>
          ))}
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn-primary" type="submit" disabled={busy}>{busy ? "Generating…" : "Generate"}</button>
          </div>
        </form>
        {result && (
          <div style={{ marginTop: 14, borderTop: "1px solid #e8ecf7", paddingTop: 12 }}>
            <HubBlocks data={result} />
            <div className="row" style={{ marginTop: 10 }}>
              <button className="btn-secondary" onClick={saveToLibrary}>Save to brand library</button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
