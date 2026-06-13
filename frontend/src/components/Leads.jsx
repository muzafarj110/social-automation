import { useEffect, useState } from "react";
import { listLeads, createLead, updateLead, deleteLead, draftOutreach } from "../api.js";

const STATUSES = ["new", "contacted", "qualified", "won", "lost"];

export default function Leads({ refreshUser }) {
  const [leads, setLeads] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", handle: "", platform: "", source: "", notes: "" });

  const load = () => listLeads().then(setLeads).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  const wrap = (fn) => async (...a) => {
    setErr(""); setBusy(true);
    try { await fn(...a); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  const add = wrap(async (e) => {
    e.preventDefault();
    if (!form.name.trim()) throw new Error("Add a name.");
    await createLead(form);
    setForm({ name: "", handle: "", platform: "", source: "", notes: "" });
    load();
  });
  const setStatus = wrap(async (id, status) => { await updateLead(id, { status }); load(); });
  const remove = wrap(async (id) => { await deleteLead(id); load(); });
  const draft = wrap(async (id) => { await draftOutreach(id); load(); refreshUser && refreshUser(); });

  return (
    <>
      {err && <div className="error">{err}</div>}

      <div className="card">
        <h2>Add a lead</h2>
        <form onSubmit={add}>
          <div className="grid-2">
            <div><label>Name</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Jane Doe" /></div>
            <div><label>Handle / email</label>
              <input value={form.handle} onChange={(e) => setForm({ ...form, handle: e.target.value })} placeholder="@jane or jane@co.com" /></div>
          </div>
          <div className="grid-2">
            <div><label>Platform</label>
              <input value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })} placeholder="linkedin" /></div>
            <div><label>Source</label>
              <input value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} placeholder="comment, referral…" /></div>
          </div>
          <label>Notes</label>
          <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} />
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn-primary" disabled={busy} type="submit">Add lead</button>
          </div>
        </form>
      </div>

      <div className="card">
        <h2>Your leads</h2>
        {!leads ? <div className="empty">Loading…</div>
          : leads.length === 0 ? <div className="empty">No leads yet. Add one above.</div>
          : (
            <div className="pill-list">
              {leads.map((l) => (
                <div className="pill" key={l.id} style={{ flexDirection: "column", alignItems: "stretch", gap: 8 }}>
                  <div className="row" style={{ alignItems: "center" }}>
                    <strong>{l.name}</strong>
                    {l.handle && <span className="muted">{l.handle}</span>}
                    {l.platform && <span className="badge kind">{l.platform}</span>}
                    <div className="spacer" />
                    <select value={l.status} onChange={(e) => setStatus(l.id, e.target.value)} disabled={busy}>
                      {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <button className="btn-secondary" disabled={busy} onClick={() => draft(l.id)}>Draft outreach</button>
                    <button className="btn-danger" disabled={busy} onClick={() => remove(l.id)}>Delete</button>
                  </div>
                  {l.notes && <div className="muted" style={{ fontSize: 13 }}>{l.notes}</div>}
                  {l.draft && (
                    <div style={{ background: "#faf9ff", border: "1px solid #ece9fb", borderRadius: 8, padding: 10, fontSize: 13 }}>
                      <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>AI-drafted outreach</div>
                      {l.draft}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
      </div>
    </>
  );
}
