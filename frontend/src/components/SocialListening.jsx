import { useEffect, useState } from "react";
import { listTopics, createTopic, deleteTopic, scanTopic } from "../api.js";

const PLATFORM_OPTS = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "twitter", label: "X / Twitter" },
  { value: "instagram", label: "Instagram" },
  { value: "facebook", label: "Facebook" },
  { value: "tiktok", label: "TikTok" },
  { value: "youtube", label: "YouTube" },
  { value: "reddit", label: "Reddit" },
  { value: "pinterest", label: "Pinterest" },
  { value: "threads", label: "Threads" },
  { value: "bluesky", label: "Bluesky" },
  { value: "all", label: "All platforms" },
];

export default function SocialListening() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [form, setForm] = useState({ keyword: "", description: "", platform: "linkedin" });
  const [adding, setAdding] = useState(false);

  const load = async () => {
    try { setRows(await listTopics()); }
    catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!form.keyword.trim()) return;
    setAdding(true); setError("");
    try {
      await createTopic({
        keyword: form.keyword.trim(),
        description: form.description.trim() || null,
        platform: form.platform,
      });
      setForm({ keyword: "", description: "", platform: "linkedin" });
      await load();
    } catch (e) { setError(e.message); }
    finally { setAdding(false); }
  };

  const scan = async (id) => {
    setBusyId(id); setError("");
    try {
      const updated = await scanTopic(id);
      setRows((r) => r.map((t) => (t.id === id ? updated : t)));
    } catch (e) { setError(e.message); }
    finally { setBusyId(null); }
  };

  const remove = async (id) => {
    if (!window.confirm("Stop monitoring this topic?")) return;
    try { await deleteTopic(id); setRows((r) => r.filter((t) => t.id !== id)); }
    catch (e) { setError(e.message); }
  };

  if (rows === null) return <div className="empty">Loading…</div>;

  return (
    <>
      {error && <div className="error" role="alert">{error}</div>}

      <div className="card aicard">
        <h2 style={{ marginBottom: 4 }}>Track a keyword or topic</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Your listening agent scans for high-intent conversations and surfaces prospects ready to engage or buy.
        </p>
        <form onSubmit={add}>
          <div className="grid-2">
            <div>
              <label>Keyword / topic</label>
              <input
                value={form.keyword}
                onChange={(e) => setForm({ ...form, keyword: e.target.value })}
                placeholder="e.g. LinkedIn automation tool"
                required
              />
            </div>
            <div>
              <label>Platform</label>
              <select
                value={form.platform}
                onChange={(e) => setForm({ ...form, platform: e.target.value })}
              >
                {PLATFORM_OPTS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>
          <label>What signals are you looking for? <span className="muted">(optional)</span></label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="e.g. founders frustrated with manual LinkedIn outreach, asking for a better tool…"
            style={{ minHeight: 70 }}
          />
          <div style={{ marginTop: 12 }}>
            <button className="btn-primary" disabled={adding}>{adding ? "Adding…" : "Add topic"}</button>
          </div>
        </form>
      </div>

      {rows.length === 0 ? (
        <div className="empty">No topics tracked yet. Add one above to start finding high-intent prospects.</div>
      ) : (
        rows.map((t) => {
          const busy = busyId === t.id;
          const plat = PLATFORM_OPTS.find((o) => o.value === t.platform)?.label || t.platform;
          return (
            <div className="card" key={t.id}>
              <div className="row" style={{ alignItems: "center" }}>
                <div>
                  <h2 style={{ margin: 0 }}>{t.keyword}</h2>
                  <span className="badge" style={{ background: "#e6f5f2", color: "#2a8c84", marginTop: 4, display: "inline-block" }}>{plat}</span>
                </div>
                <div className="spacer" />
                <button className="btn-primary" onClick={() => scan(t.id)} disabled={busy}>
                  {busy ? <><span className="spinner" />Scanning…</> : t.results ? "Re-scan (1 credit)" : "Scan (1 credit)"}
                </button>
                <button className="btn-ghost" onClick={() => remove(t.id)} title="Remove" aria-label="Remove">✕</button>
              </div>

              {t.description && (
                <p className="muted" style={{ fontSize: 13, marginTop: 8 }}>{t.description}</p>
              )}

              {t.results ? (
                <div className="res-section" style={{ marginTop: 12 }}>
                  {t.results.summary && (
                    <div className="res-callout" style={{ marginBottom: 12 }}>{t.results.summary}</div>
                  )}

                  {t.results.signals?.length > 0 && (
                    <>
                      <div className="res-h">High-intent signals &amp; prospect patterns</div>
                      <ul className="res-list">
                        {t.results.signals.map((s, i) => <li key={i}>{s}</li>)}
                      </ul>
                    </>
                  )}

                  {t.results.actions?.length > 0 && (
                    <>
                      <div className="res-h" style={{ marginTop: 12 }}>Recommended engagement actions</div>
                      <ul className="res-list">
                        {t.results.actions.map((a, i) => <li key={i}>{a}</li>)}
                      </ul>
                    </>
                  )}

                  {t.scanned_at && (
                    <div className="res-kv" style={{ marginTop: 10 }}>
                      Last scanned {new Date(t.scanned_at).toLocaleString()}
                    </div>
                  )}
                </div>
              ) : (
                <div className="muted" style={{ fontSize: 13, marginTop: 10 }}>
                  Not scanned yet — run a scan to surface prospects and signals.
                </div>
              )}
            </div>
          );
        })
      )}
    </>
  );
}
