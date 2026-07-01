import { useEffect, useState } from "react";
import { adminListUsers, adminFeatures, adminUpdateUser, adminDeleteUser, adminEmailConfig, adminTestEmail } from "../api.js";

const PLANS = ["free", "pro", "business"];

function EmailDiagPanel() {
  const [cfg, setCfg] = useState(null);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState(null);
  const [testTo, setTestTo] = useState("");

  useEffect(() => { adminEmailConfig().then(setCfg).catch(() => {}); }, []);

  const runTest = async () => {
    setTesting(true); setResult(null);
    try {
      const r = await adminTestEmail(testTo.trim() || undefined);
      setResult(r);
    } catch (e) {
      setResult({ ok: false, error: e.message });
    } finally { setTesting(false); }
  };

  if (!cfg) return null;

  const baseUrlMissing = cfg.app_base_url.includes("(not set)");

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <h3 style={{ margin: "0 0 12px" }}>Email delivery diagnostics</h3>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 6, fontSize: 13, marginBottom: 12 }}>
        <KV k="Resend API key" v={cfg.resend_api_key_set ? "●●●●●●●● (set)" : "NOT SET"} warn={!cfg.resend_api_key_set} />
        <KV k="From address" v={cfg.resend_from} />
        <KV k="APP_BASE_URL" v={cfg.app_base_url} warn={baseUrlMissing} />
      </div>

      {baseUrlMissing && (
        <div style={{ marginBottom: 12, padding: "10px 14px", borderRadius: 8, background: "#fef9c3", border: "1px solid #fde047", fontSize: 13, color: "#854d0e" }}>
          <b>⚠ APP_BASE_URL is missing in Railway.</b><br />
          Verify and reset links in emails will be broken — the link just says <code>/#verify?token=...</code> with no domain, so it goes nowhere when clicked.<br />
          <b>Fix:</b> Add <code>APP_BASE_URL = https://autopilot-io.up.railway.app</code> in Railway Variables.
        </div>
      )}

      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <input
          type="email"
          placeholder="Send test to (leave blank for admin email)"
          value={testTo}
          onChange={(e) => setTestTo(e.target.value)}
          style={{ flex: 1, minWidth: 220, padding: "8px 12px", borderRadius: 8, border: "1px solid #d9d9e3", fontSize: 13 }}
        />
        <button className="btn-secondary" onClick={runTest} disabled={testing || !cfg.email_enabled}>
          {testing ? "Sending…" : "Send test email →"}
        </button>
      </div>
      {!cfg.email_enabled && (
        <p className="muted" style={{ fontSize: 12, margin: "6px 0 0" }}>Set RESEND_API_KEY in Railway to enable.</p>
      )}

      {result && (
        <div style={{
          marginTop: 12, padding: "12px 14px", borderRadius: 8, fontSize: 13,
          background: result.ok ? "#f0fdf4" : "#fef2f2",
          color: result.ok ? "#166534" : "#991b1b",
          border: `1px solid ${result.ok ? "#bbf7d0" : "#fecaca"}`,
        }}>
          {result.ok ? (
            <>
              <b>✓ Email sent to {result.sent_to}</b><br />
              <span style={{ fontSize: 12 }}>APP_BASE_URL: {result.app_base_url}</span><br />
              <span style={{ fontSize: 12 }}>Check inbox + spam. If it arrived, Resend is working. If the link inside doesn't work → APP_BASE_URL is wrong.</span>
            </>
          ) : (
            <>
              <b>✗ Failed</b><br />
              <span style={{ fontSize: 12 }}>{result.error}</span>
              {result.resend_response && <><br /><span style={{ fontSize: 11, opacity: 0.7 }}>Resend response: {result.resend_response}</span></>}
            </>
          )}
        </div>
      )}
    </div>
  );
}

const KV = ({ k, v, warn }) => (
  <div style={{ padding: "6px 10px", background: "#f8f8fc", borderRadius: 6 }}>
    <div className="muted" style={{ fontSize: 11 }}>{k}</div>
    <div style={{ fontWeight: 500, color: warn ? "#ef4444" : "inherit" }}>{v}</div>
  </div>
);

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [features, setFeatures] = useState([]);
  const [planFeatures, setPlanFeatures] = useState({});
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [expanded, setExpanded] = useState(null);
  const [savingId, setSavingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const [u, f] = await Promise.all([adminListUsers(), adminFeatures()]);
      setUsers(u);
      setFeatures(f.features || []);
      setPlanFeatures(f.plan_features || {});
    } catch (e) {
      setErr(e.message || "Couldn't load users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const patch = async (id, data) => {
    setSavingId(id);
    try {
      const updated = await adminUpdateUser(id, data);
      setUsers((list) => list.map((u) => (u.id === id ? updated : u)));
    } catch (e) {
      setErr(e.message || "Update failed");
    } finally {
      setSavingId(null);
    }
  };

  const setPlan = (u, plan) => patch(u.id, { plan });
  const toggleStatus = (u) =>
    patch(u.id, { status: u.status === "active" ? "suspended" : "active" });

  const deleteUser = async (u) => {
    if (!window.confirm(`Delete ${u.email}? This cannot be undone.`)) return;
    setDeletingId(u.id);
    try {
      await adminDeleteUser(u.id);
      setUsers((list) => list.filter((x) => x.id !== u.id));
    } catch (e) {
      setErr(e.message || "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  // Toggle a single feature override for a user. We start from their current
  // effective entitlements so flipping one feature doesn't drop the others.
  const toggleFeature = (u, feat) => {
    const base = { ...(u.entitlements_override || {}) };
    const current = u.entitlements?.[feat] === true;
    base[feat] = !current;
    patch(u.id, { entitlements_override: base });
  };
  const clearOverrides = (u) => patch(u.id, { entitlements_override: {} });

  if (loading) return <div className="empty">Loading users…</div>;

  const counts = PLANS.reduce(
    (acc, p) => ({ ...acc, [p]: users.filter((u) => u.plan === p).length }),
    {}
  );
  const suspended = users.filter((u) => u.status === "suspended").length;

  return (
    <div>
      {err && <div className="error" style={{ marginBottom: 12 }}>{err}</div>}

      <EmailDiagPanel />

      <div className="kpi-strip">
        <div className="kpi-tile"><div className="v">{users.length}</div><div className="l">Total users</div></div>
        <div className="kpi-tile"><div className="v">{counts.free}</div><div className="l">Free</div></div>
        <div className="kpi-tile"><div className="v">{counts.pro}</div><div className="l">Pro</div></div>
        <div className="kpi-tile"><div className="v">{counts.business}</div><div className="l">Business</div></div>
        <div className="kpi-tile"><div className="v">{suspended}</div><div className="l">Suspended</div></div>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--muted, #6b6b80)", fontSize: 12 }}>
              <Th>User</Th>
              <Th>Plan</Th>
              <Th>Status</Th>
              <Th>Keys</Th>
              <Th>Accounts</Th>
              <Th>Joined</Th>
              <Th>Features</Th>
              <Th></Th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <UserRow
                key={u.id}
                u={u}
                features={features}
                planFeatures={planFeatures}
                saving={savingId === u.id}
                deleting={deletingId === u.id}
                expanded={expanded === u.id}
                onExpand={() => setExpanded(expanded === u.id ? null : u.id)}
                onPlan={setPlan}
                onStatus={toggleStatus}
                onFeature={toggleFeature}
                onClear={clearOverrides}
                onDelete={deleteUser}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UserRow({ u, features, planFeatures, saving, deleting, expanded, onExpand, onPlan, onStatus, onFeature, onClear, onDelete }) {
  const hasOverride = u.entitlements_override && Object.keys(u.entitlements_override).length > 0;
  return (
    <>
      <tr style={{ borderTop: "1px solid #ececf3", opacity: (saving || deleting) ? 0.5 : 1 }}>
        <td style={td}>
          <div style={{ fontWeight: 600 }}>
            {u.full_name || u.email}
            {u.is_admin && <span className="badge" style={{ marginLeft: 8 }}>ADMIN</span>}
          </div>
          <div className="muted" style={{ fontSize: 12 }}>{u.email}{u.profile_type ? ` · ${u.profile_type}` : ""}</div>
        </td>
        <td style={td}>
          <select value={u.plan} disabled={u.is_admin || saving}
            onChange={(e) => onPlan(u, e.target.value)} style={selectStyle}>
            {PLANS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </td>
        <td style={td}>
          <button className={u.status === "active" ? "btn-ghost" : "btn-danger"}
            disabled={u.is_admin || saving} onClick={() => onStatus(u)}
            style={{ fontSize: 12, padding: "4px 10px" }}>
            {u.status === "active" ? "Active" : "Suspended"}
          </button>
        </td>
        <td style={td}>
          <span title="Hub key" style={{ opacity: u.has_hub_key ? 1 : 0.3 }}>Hub</span>{" · "}
          <span title="Zernio key" style={{ opacity: u.has_zernio_key ? 1 : 0.3 }}>Zernio</span>
        </td>
        <td style={td}>{u.account_count}</td>
        <td style={td} className="muted">{new Date(u.created_at).toLocaleDateString()}</td>
        <td style={td}>
          <button className="btn-ghost" onClick={onExpand} style={{ fontSize: 12, padding: "4px 10px" }}>
            {expanded ? "Hide" : "Edit"}{hasOverride && !expanded ? " *" : ""}
          </button>
        </td>
        <td style={td}>
          {!u.is_admin && (
            <button
              onClick={() => onDelete(u)}
              disabled={saving || deleting}
              style={{ fontSize: 12, padding: "4px 10px", background: "none", border: "1px solid #fca5a5", color: "#ef4444", borderRadius: 6, cursor: "pointer" }}
            >
              {deleting ? "…" : "Delete"}
            </button>
          )}
        </td>
      </tr>
      {expanded && (
        <tr style={{ background: "#faf9ff" }}>
          <td style={{ padding: 16 }} colSpan={7}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <div className="muted" style={{ fontSize: 12 }}>
                Toggle features for this user (overrides their <b>{u.plan}</b> plan).
              </div>
              {hasOverride && (
                <button className="btn-ghost" onClick={() => onClear(u)} style={{ fontSize: 12 }}>
                  Reset to plan defaults
                </button>
              )}
            </div>
            <div className="feat-grid">
              {features.map((f) => {
                const on = u.entitlements?.[f] === true;
                const disabled = u.is_admin || saving;
                return (
                  <div key={f} className={`feat-chip${on ? " on" : ""}${disabled ? " disabled" : ""}`}
                    onClick={() => { if (!disabled) onFeature(u, f); }}>
                    <span style={{ textTransform: "capitalize" }}>{f.replace(/_/g, " ")}</span>
                    <span className="sw" aria-hidden="true" />
                  </div>
                );
              })}
            </div>
            {u.is_admin && <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>Admin accounts always have every feature.</div>}
          </td>
        </tr>
      )}
    </>
  );
}

function Stat({ label, value }) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

const Th = ({ children }) => <th style={{ padding: "12px 14px", fontWeight: 600 }}>{children}</th>;
const td = { padding: "12px 14px", verticalAlign: "top" };
const selectStyle = { padding: "5px 8px", borderRadius: 8, border: "1px solid #d9d9e3", background: "#fff", fontSize: 13 };
