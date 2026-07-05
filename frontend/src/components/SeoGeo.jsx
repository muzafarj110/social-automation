import { useEffect, useState } from "react";
import { listSeoProjects, createSeoProject, deleteSeoProject, analyzeSeoProject } from "../api.js";

export default function SeoGeo() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [form, setForm] = useState({ website: "", target_keywords: "", audience: "" });
  const [adding, setAdding] = useState(false);
  const [tab, setTab] = useState({});  // per-card active tab: keywords | geo | technical

  const load = async () => {
    try { setRows(await listSeoProjects()); }
    catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!form.target_keywords.trim()) return;
    setAdding(true); setError("");
    try {
      await createSeoProject({
        website: form.website.trim() || null,
        target_keywords: form.target_keywords.trim(),
        audience: form.audience.trim() || null,
      });
      setForm({ website: "", target_keywords: "", audience: "" });
      await load();
    } catch (e) { setError(e.message); }
    finally { setAdding(false); }
  };

  const analyze = async (id) => {
    setBusyId(id); setError("");
    try {
      const updated = await analyzeSeoProject(id);
      setRows((r) => r.map((p) => (p.id === id ? updated : p)));
    } catch (e) { setError(e.message); }
    finally { setBusyId(null); }
  };

  const remove = async (id) => {
    if (!window.confirm("Remove this SEO project?")) return;
    try { await deleteSeoProject(id); setRows((r) => r.filter((p) => p.id !== id)); }
    catch (e) { setError(e.message); }
  };

  const cardTab = (id) => tab[id] || "keywords";
  const setCardTab = (id, t) => setTab((prev) => ({ ...prev, [id]: t }));

  if (rows === null) return <div className="empty">Loading…</div>;

  return (
    <>
      {error && <div className="error" role="alert">{error}</div>}

      <div className="card aicard">
        <h2 style={{ marginBottom: 4 }}>New SEO + GEO project</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Add a website or topic and the AI will surface keyword opportunities, technical fixes, and how to appear in AI chatbot answers (GEO).
        </p>
        <form onSubmit={add}>
          <div className="grid-2">
            <div>
              <label>Website <span className="muted">(optional)</span></label>
              <input
                value={form.website}
                onChange={(e) => setForm({ ...form, website: e.target.value })}
                placeholder="yoursite.com"
              />
            </div>
            <div>
              <label>Target audience <span className="muted">(optional)</span></label>
              <input
                value={form.audience}
                onChange={(e) => setForm({ ...form, audience: e.target.value })}
                placeholder="e.g. B2B SaaS founders"
              />
            </div>
          </div>
          <label>Keywords / topics to rank for</label>
          <textarea
            value={form.target_keywords}
            onChange={(e) => setForm({ ...form, target_keywords: e.target.value })}
            placeholder="e.g. LinkedIn automation, AI marketing tools, B2B lead generation…"
            style={{ minHeight: 70 }}
            required
          />
          <div style={{ marginTop: 12 }}>
            <button className="btn-primary" disabled={adding}>{adding ? "Adding…" : "Add project"}</button>
          </div>
        </form>
      </div>

      {rows.length === 0 ? (
        <div className="empty">No SEO projects yet. Add one above to get keyword and GEO recommendations.</div>
      ) : (
        rows.map((p) => {
          const busy = busyId === p.id;
          const active = cardTab(p.id);
          const res = p.results;
          return (
            <div className="card" key={p.id}>
              <div className="row" style={{ alignItems: "center" }}>
                <div>
                  <h2 style={{ margin: 0 }}>{p.website || p.target_keywords.slice(0, 40)}</h2>
                  {p.website && (
                    <a href={p.website.startsWith("http") ? p.website : `https://${p.website}`}
                       target="_blank" rel="noreferrer" style={{ fontSize: 13 }}>{p.website}</a>
                  )}
                </div>
                <div className="spacer" />
                <button className="btn-primary" onClick={() => analyze(p.id)} disabled={busy}>
                  {busy
                    ? <><span className="spinner" />Analyzing…</>
                    : res ? "Re-analyze (2 credits)" : "Analyze (2 credits)"}
                </button>
                <button className="btn-ghost" onClick={() => remove(p.id)} title="Remove" aria-label="Remove">✕</button>
              </div>

              <p className="muted" style={{ fontSize: 13, marginTop: 6 }}>
                <strong>Keywords:</strong> {p.target_keywords}
                {p.audience && <> · <strong>Audience:</strong> {p.audience}</>}
              </p>

              {res ? (
                <div style={{ marginTop: 12 }}>
                  {res.summary && (
                    <div className="res-callout" style={{ marginBottom: 14 }}>{res.summary}</div>
                  )}

                  {/* Tab switcher */}
                  <div className="row" style={{ gap: 4, marginBottom: 14 }}>
                    {[
                      ["keywords", "Keyword opportunities"],
                      ["geo", "GEO — AI visibility"],
                      ["technical", "Technical fixes"],
                    ].map(([key, label]) => (
                      <button
                        key={key}
                        onClick={() => setCardTab(p.id, key)}
                        style={{
                          fontSize: 12.5, fontWeight: 600, padding: "5px 12px",
                          borderRadius: 999, border: "none", cursor: "pointer",
                          background: active === key ? "var(--teal)" : "var(--light)",
                          color: active === key ? "#fff" : "var(--teal-dark)",
                        }}
                      >{label}</button>
                    ))}
                  </div>

                  {active === "keywords" && (
                    res.keywords?.length > 0
                      ? <ul className="res-list">{res.keywords.map((k, i) => <li key={i}>{k}</li>)}</ul>
                      : <div className="muted" style={{ fontSize: 13 }}>No keyword data returned — try re-analyzing with more specific topics.</div>
                  )}

                  {active === "geo" && (
                    res.geo?.length > 0
                      ? <>
                          <p className="muted" style={{ fontSize: 13, marginBottom: 10 }}>
                            How to get cited in ChatGPT, Perplexity, Claude and other AI chatbot answers.
                          </p>
                          <ul className="res-list">{res.geo.map((g, i) => <li key={i}>{g}</li>)}</ul>
                        </>
                      : <div className="muted" style={{ fontSize: 13 }}>No GEO data returned — try re-analyzing.</div>
                  )}

                  {active === "technical" && (
                    res.technical?.length > 0
                      ? <ul className="res-list">{res.technical.map((t, i) => <li key={i}>{t}</li>)}</ul>
                      : <div className="muted" style={{ fontSize: 13 }}>No technical recommendations returned — try re-analyzing.</div>
                  )}

                  {p.analyzed_at && (
                    <div className="res-kv" style={{ marginTop: 14 }}>
                      Last analyzed {new Date(p.analyzed_at).toLocaleString()}
                    </div>
                  )}
                </div>
              ) : (
                <div className="muted" style={{ fontSize: 13, marginTop: 10 }}>
                  Not analyzed yet — run a full analysis to get keyword opportunities, GEO recommendations, and technical fixes.
                </div>
              )}
            </div>
          );
        })
      )}
    </>
  );
}
