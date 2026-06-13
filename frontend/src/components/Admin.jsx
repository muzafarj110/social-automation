import { useEffect, useState } from "react";
import { adminListUsers, adminFeatures, adminUpdateUser } from "../api.js";

const PLANS = ["free", "pro", "business"];

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [features, setFeatures] = useState([]);
  const [planFeatures, setPlanFeatures] = useState({});
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [expanded, setExpanded] = useState(null); // user id whose features are open
  const [savingId, setSavingId] = useState(null);

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

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <Stat label="Total users" value={users.length} />
        <Stat label="Free" value={counts.free} />
        <Stat label="Pro" value={counts.pro} />
        <Stat label="Business" value={counts.business} />
        <Stat label="Suspended" value={suspended} />
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
                expanded={expanded === u.id}
                onExpand={() => setExpanded(expanded === u.id ? null : u.id)}
                onPlan={setPlan}
                onStatus={toggleStatus}
                onFeature={toggleFeature}
                onClear={clearOverrides}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UserRow({ u, features, planFeatures, saving, expanded, onExpand, onPlan, onStatus, onFeature, onClear }) {
  const hasOverride = u.entitlements_override && Object.keys(u.entitlements_override).length > 0;
  return (
    <>
      <tr style={{ borderTop: "1px solid #ececf3", opacity: saving ? 0.5 : 1 }}>
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
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 8 }}>
              {features.map((f) => {
                const on = u.entitlements?.[f] === true;
                const planDefault = planFeatures[u.plan]?.[f] === true;
                const overridden = u.entitlements_override && f in u.entitlements_override;
                return (
                  <label key={f} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: u.is_admin ? "default" : "pointer" }}>
                    <input type="checkbox" checked={on} disabled={u.is_admin || saving}
                      onChange={() => onFeature(u, f)} />
                    <span>{f.replace(/_/g, " ")}</span>
                    {overridden && <span className="badge" style={{ fontSize: 9 }}>{on === planDefault ? "" : "OVR"}</span>}
                  </label>
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
