import { useEffect, useState } from "react";
import { listCompetitors, createCompetitor, deleteCompetitor, analyzeCompetitor } from "../api.js";

// Competitor Strategy agent — track rivals and let AI surface tactics worth
// copying and positioning gaps to exploit.
export default function Competitor() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [form, setForm] = useState({ name: "", website: "", notes: "" });
  const [adding, setAdding] = useState(false);

  const load = async () => {
    try { setRows(await listCompetitors()); }
    catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setAdding(true); setError("");
    try {
      await createCompetitor({ name: form.name.trim(), website: form.website.trim() || null, notes: form.notes.trim() || null });
      setForm({ name: "", website: "", notes: "" });
      await load();
    } catch (e) { setError(e.message); }
    finally { setAdding(false); }
  };

  const analyze = async (id) => {
    setBusyId(id); setError("");
    try { const updated = await analyzeCompetitor(id); setRows((r) => r.map((c) => (c.id === id ? updated : c))); }
    catch (e) { setError(e.message); }
    finally { setBusyId(null); }
  };

  const remove = async (id) => {
    if (!window.confirm("Stop tracking this competitor?")) return;
    try { await deleteCompetitor(id); setRows((r) => r.filter((c) => c.id !== id)); }
    catch (e) { setError(e.message); }
  };

  if (rows === null) return <div className="empty">Loading…</div>;

  return (
    <>
      {error && <div className="error" role="alert">{error}</div>}

      <div className="card aicard">
        <h2 style={{ marginBottom: 4 }}>Track a competitor</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Add a rival and your competitor agent will analyze their tactics — what's working and where the gaps are.
        </p>
        <form onSubmit={add}>
          <div className="grid-2">
            <div>
              <label htmlFor="comp-name">Name</label>
              <input id="comp-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Brandly" required />
            </div>
            <div>
              <label htmlFor="comp-website">Website <span className="muted">(optional)</span></label>
              <input id="comp-website" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} placeholder="brandly.com" />
            </div>
          </div>
          <label htmlFor="comp-notes">What do you know about them? <span className="muted">(optional)</span></label>
          <textarea id="comp-notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="Their positioning, channels, recent campaigns…" style={{ minHeight: 70 }} />
          <div style={{ marginTop: 12 }}>
            <button className="btn-primary" disabled={adding}>{adding ? "Adding…" : "Add competitor"}</button>
          </div>
        </form>
      </div>

      {rows.length === 0 ? (
        <div className="empty">No competitors tracked yet. Add one above to get your first analysis.</div>
      ) : (
        rows.map((c) => (
          <div className="card" key={c.id}>
            <div className="row" style={{ alignItems: "center" }}>
              <div>
                <h2 style={{ margin: 0 }}>{c.name}</h2>
                {c.website && <a href={c.website.startsWith("http") ? c.website : `https://${c.website}`} target="_blank" rel="noreferrer" style={{ fontSize: 13 }}>{c.website}</a>}
              </div>
              <div className="spacer" />
              <button className="btn-primary" onClick={() => analyze(c.id)} disabled={busyId === c.id}>
                {busyId === c.id ? <><span className="spinner" />Analyzing…</> : c.analysis ? "Re-analyze" : "Analyze (1 credit)"}
              </button>
              <button className="btn-ghost" onClick={() => remove(c.id)} title="Remove" aria-label="Remove">✕</button>
            </div>

            {c.notes && <p className="muted" style={{ fontSize: 13, marginTop: 8 }}>{c.notes}</p>}

            {c.analysis ? (
              <div className="res-section" style={{ marginTop: 12 }}>
                {c.analysis.summary && (
                  <div className="res-callout" style={{ marginBottom: 12 }}>{c.analysis.summary}</div>
                )}
                {c.analysis.tactics?.length > 0 && (
                  <>
                    <div className="res-h">Tactics worth copying</div>
                    <ul className="res-list">{c.analysis.tactics.map((t, i) => <li key={i}>{t}</li>)}</ul>
                  </>
                )}
                {c.analysis.gaps?.length > 0 && (
                  <>
                    <div className="res-h" style={{ marginTop: 12 }}>Gaps to exploit</div>
                    <ul className="res-list">{c.analysis.gaps.map((g, i) => <li key={i}>{g}</li>)}</ul>
                  </>
                )}
                {c.analyzed_at && <div className="res-kv" style={{ marginTop: 10 }}>Last analyzed {new Date(c.analyzed_at).toLocaleString()}</div>}
              </div>
            ) : (
              <div className="muted" style={{ fontSize: 13, marginTop: 10 }}>Not analyzed yet — run an analysis to see tactics and gaps.</div>
            )}
          </div>
        ))
      )}
    </>
  );
}
