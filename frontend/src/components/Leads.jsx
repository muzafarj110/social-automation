import { useEffect, useState } from "react";
import { listLeads, createLead, updateLead, deleteLead, draftOutreach } from "../api.js";

const STAGES = [
  { value: "new",        label: "New",        bg: "#e6f5f2", fg: "#2a8c84" },
  { value: "contacted",  label: "Contacted",  bg: "#e6f1fb", fg: "#185FA5" },
  { value: "qualified",  label: "Qualified",  bg: "#fff8e6", fg: "#7A5200" },
  { value: "won",        label: "Won",        bg: "#dcfce7", fg: "#166534" },
  { value: "lost",       label: "Lost",       bg: "#fee2e2", fg: "#991b1b" },
];

const PLATFORMS = ["LinkedIn", "X / Twitter", "Email", "Referral", "Other"];

function StageBadge({ value, onChange }) {
  const s = STAGES.find((x) => x.value === value) || STAGES[0];
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        fontSize: 12, fontWeight: 700, padding: "4px 10px", borderRadius: 999,
        border: "none", cursor: "pointer", appearance: "none",
        background: s.bg, color: s.fg,
      }}
    >
      {STAGES.map((st) => <option key={st.value} value={st.value}>{st.label}</option>)}
    </select>
  );
}

export default function Leads({ refreshUser }) {
  const [leads, setLeads] = useState(null);
  const [err, setErr] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [form, setForm] = useState({ name: "", handle: "", platform: "LinkedIn", source: "", notes: "" });
  const [adding, setAdding] = useState(false);
  const [copied, setCopied] = useState(null);

  const load = async () => {
    try { setLeads(await listLeads()); }
    catch (e) { setErr(e.message); }
  };
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setAdding(true); setErr("");
    try {
      await createLead({
        name: form.name.trim(),
        handle: form.handle.trim() || null,
        platform: form.platform,
        source: form.source.trim() || null,
        notes: form.notes.trim() || null,
      });
      setForm({ name: "", handle: "", platform: "LinkedIn", source: "", notes: "" });
      await load();
    } catch (e) { setErr(e.message); }
    finally { setAdding(false); }
  };

  const changeStatus = async (id, status) => {
    try { const updated = await updateLead(id, { status }); setLeads((l) => l.map((x) => (x.id === id ? updated : x))); }
    catch (e) { setErr(e.message); }
  };

  const draft = async (id) => {
    setBusyId(id); setErr("");
    try {
      const updated = await draftOutreach(id);
      setLeads((l) => l.map((x) => (x.id === id ? updated : x)));
      refreshUser && refreshUser();
    } catch (e) { setErr(e.message); }
    finally { setBusyId(null); }
  };

  const remove = async (id) => {
    if (!window.confirm("Remove this prospect?")) return;
    try { await deleteLead(id); setLeads((l) => l.filter((x) => x.id !== id)); }
    catch (e) { setErr(e.message); }
  };

  const copy = (id, text) => {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  if (leads === null) return <div className="empty">Loading your prospects…</div>;

  return (
    <>
      {err && <div className="error">{err}</div>}

      {/* Add prospect form */}
      <div className="card aicard">
        <h2 style={{ marginBottom: 4 }}>Add a prospect</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Your lead-gen agent will draft a personalised outreach message — you approve before anything sends.
        </p>
        <form onSubmit={add}>
          <div className="grid-2">
            <div>
              <label>Name</label>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Sarah Chen"
                required
              />
            </div>
            <div>
              <label>Handle / email <span className="muted">(optional)</span></label>
              <input
                value={form.handle}
                onChange={(e) => setForm({ ...form, handle: e.target.value })}
                placeholder="@sarahchen or sarah@co.com"
              />
            </div>
          </div>
          <div className="grid-2">
            <div>
              <label>Platform</label>
              <select value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })}>
                {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label>How did you find them? <span className="muted">(optional)</span></label>
              <input
                value={form.source}
                onChange={(e) => setForm({ ...form, source: e.target.value })}
                placeholder="e.g. commented on your post"
              />
            </div>
          </div>
          <label>What's their pain or goal? <span className="muted">(drives the AI outreach)</span></label>
          <textarea
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="e.g. Frustrated with manual LinkedIn outreach, growing a SaaS to $1M ARR, asked about automation tools…"
            style={{ minHeight: 70 }}
          />
          <div style={{ marginTop: 12 }}>
            <button className="btn-primary" disabled={adding}>{adding ? "Adding…" : "Add prospect"}</button>
          </div>
        </form>
      </div>

      {/* Pipeline summary */}
      {leads.length > 0 && (
        <div className="card" style={{ padding: "14px 18px", marginBottom: 12 }}>
          <div className="row" style={{ alignItems: "center", flexWrap: "wrap", gap: 8 }}>
            <span style={{ fontWeight: 700, fontSize: 13.5 }}>{leads.length} prospect{leads.length === 1 ? "" : "s"}</span>
            <div className="spacer" />
            {STAGES.map((s) => {
              const count = leads.filter((l) => l.status === s.value).length;
              if (!count) return null;
              return (
                <span key={s.value} style={{
                  fontSize: 12, fontWeight: 600, padding: "3px 10px", borderRadius: 999,
                  background: s.bg, color: s.fg,
                }}>{s.label}: {count}</span>
              );
            })}
          </div>
        </div>
      )}

      {leads.length === 0 ? (
        <div className="empty">No prospects yet. Add one above and your lead-gen agent will draft the outreach.</div>
      ) : (
        leads.map((l) => {
          const busy = busyId === l.id;
          return (
            <div className="card" key={l.id}>
              {/* Header row */}
              <div className="row" style={{ alignItems: "flex-start", flexWrap: "nowrap", gap: 12 }}>
                {/* Avatar */}
                <span style={{
                  width: 40, height: 40, borderRadius: 10, flexShrink: 0,
                  display: "grid", placeItems: "center",
                  background: "#fbeaf0", color: "#993556",
                  fontWeight: 700, fontSize: 15,
                }}>
                  {l.name.trim().charAt(0).toUpperCase()}
                </span>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="row" style={{ alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                    <strong style={{ fontSize: 15 }}>{l.name}</strong>
                    {l.handle && (
                      <span className="muted" style={{ fontSize: 13 }}>{l.handle}</span>
                    )}
                    {l.platform && (
                      <span className="badge" style={{ background: "#e6f5f2", color: "#2a8c84" }}>{l.platform}</span>
                    )}
                    {l.source && (
                      <span className="muted" style={{ fontSize: 12 }}>via {l.source}</span>
                    )}
                  </div>
                  {l.notes && (
                    <p className="muted" style={{ fontSize: 13, margin: "4px 0 0" }}>{l.notes}</p>
                  )}
                </div>

                <div className="row" style={{ gap: 8, flexShrink: 0, alignItems: "center" }}>
                  <StageBadge value={l.status} onChange={(s) => changeStatus(l.id, s)} />
                  <button className="btn-ghost" onClick={() => remove(l.id)} title="Remove prospect">✕</button>
                </div>
              </div>

              {/* Action row */}
              <div className="row" style={{ marginTop: 12, marginLeft: 52 }}>
                <button className="btn-primary" style={{ fontSize: 13, padding: "8px 16px" }}
                  onClick={() => draft(l.id)} disabled={busy}>
                  {busy
                    ? <><span className="spinner" />Drafting…</>
                    : l.draft ? "Re-draft (1 credit)" : "Draft outreach (1 credit)"}
                </button>
                {l.status === "new" && (
                  <button className="btn-secondary" style={{ fontSize: 13 }}
                    onClick={() => changeStatus(l.id, "contacted")}>
                    Mark contacted
                  </button>
                )}
              </div>

              {/* AI-drafted outreach */}
              {l.draft && (
                <div className="res-section" style={{ marginTop: 14, marginLeft: 52 }}>
                  <div className="row" style={{ marginBottom: 6 }}>
                    <div className="res-h" style={{ margin: 0 }}>AI-drafted outreach</div>
                    <div className="spacer" />
                    <button
                      onClick={() => copy(l.id, l.draft)}
                      style={{
                        fontSize: 12, fontWeight: 600, padding: "3px 10px",
                        borderRadius: 999, border: "1px solid var(--line)",
                        background: copied === l.id ? "var(--teal)" : "#fff",
                        color: copied === l.id ? "#fff" : "var(--teal-dark)",
                        cursor: "pointer",
                      }}
                    >
                      {copied === l.id ? "Copied!" : "Copy"}
                    </button>
                  </div>
                  <div className="res-callout" style={{ whiteSpace: "pre-wrap" }}>{l.draft}</div>
                </div>
              )}
            </div>
          );
        })
      )}
    </>
  );
}
