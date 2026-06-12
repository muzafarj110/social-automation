import { useEffect, useState } from "react";
import {
  listAccounts,
  zernioAvailable,
  linkAccount,
  unlinkAccount,
  setHubKey,
  setZernioKey,
  getUsage,
} from "../api.js";

function UsageTile({ label, value }) {
  return (
    <div style={{
      background: "var(--light)", borderRadius: "var(--radius)", padding: "12px 16px",
      minWidth: 110, flex: "1 0 auto", textAlign: "center",
    }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: "var(--blue)" }}>{value}</div>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
    </div>
  );
}

// Render the Hub's free-form /api/me response as a clean usage panel.
function UsageCard({ data }) {
  if (!data) return null;
  const d = (data.data || data) || {};
  const norm = {};
  for (const [k, v] of Object.entries(d)) norm[k.toLowerCase().replace(/[^a-z0-9]/g, "")] = v;
  const g = (...keys) => {
    for (const k of keys) if (norm[k] !== undefined && norm[k] !== null) return norm[k];
    return undefined;
  };
  const plan = g("plan", "tier");
  const name = g("name", "fullname");
  const email = g("email");
  const today = g("callstoday", "todaycalls", "today", "dailyusage");
  const total = g("callstotal", "totalcalls", "callsused", "usage");
  const limit = g("dailylimit", "limit", "quota", "monthlylimit");
  const bonus = g("bonuscalls", "bonus");
  const refCode = g("referralcode");
  const refCount = g("referralcount");
  const fmt = (v) => (typeof v === "number" ? v.toLocaleString() : String(v));

  return (
    <div>
      <div className="row" style={{ alignItems: "center", marginBottom: 12 }}>
        {plan && <span className="badge kind" style={{ textTransform: "uppercase" }}>{String(plan)}</span>}
        <div>
          {name && <div style={{ fontWeight: 600, color: "var(--ink)" }}>{name}</div>}
          {email && <div className="muted" style={{ fontSize: 12 }}>{email}</div>}
        </div>
      </div>
      <div className="row" style={{ gap: 10 }}>
        {today !== undefined && <UsageTile label="Calls today" value={fmt(today)} />}
        {total !== undefined && <UsageTile label="Calls total" value={fmt(total)} />}
        {limit !== undefined && <UsageTile label="Daily limit" value={fmt(limit)} />}
        {bonus !== undefined && <UsageTile label="Bonus calls" value={fmt(bonus)} />}
      </div>
      {(refCode || refCount !== undefined) && (
        <div className="muted" style={{ fontSize: 12, marginTop: 12 }}>
          {refCode && <>Referral code: <strong>{refCode}</strong></>}
          {refCount !== undefined && <> · {fmt(refCount)} referrals</>}
        </div>
      )}
    </div>
  );
}

export default function Accounts({ user, accounts, reloadAccounts, refreshUser }) {
  const [available, setAvailable] = useState(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [hubKey, setHubKeyInput] = useState("");
  const [zKey, setZKeyInput] = useState("");
  const [manualId, setManualId] = useState("");
  const [manualName, setManualName] = useState("");
  const [busy, setBusy] = useState(false);
  const [usage, setUsage] = useState(null);

  useEffect(() => {
    reloadAccounts();
    getUsage().then(setUsage).catch(() => setUsage({ error: true }));
  }, []); // eslint-disable-line

  const wrap = (fn) => async (...a) => {
    setError("");
    setMsg("");
    setBusy(true);
    try {
      await fn(...a);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const saveHubKey = wrap(async () => {
    await setHubKey(hubKey.trim());
    setHubKeyInput("");
    setMsg("Hub key saved.");
    refreshUser();
  });

  const saveZernioKey = wrap(async () => {
    await setZernioKey(zKey.trim());
    setZKeyInput("");
    setMsg("Zernio key saved.");
    refreshUser();
  });

  const findZernio = wrap(async () => {
    const res = await zernioAvailable();
    // Zernio response shape can vary; normalize to a list.
    const list = res?.accounts || res?.data || (Array.isArray(res) ? res : []);
    setAvailable(list);
    if (!list.length) setMsg("No connected LinkedIn accounts found under your Zernio key.");
  });

  const doLink = wrap(async (zernio_account_id, display_name, account_type) => {
    await linkAccount({ zernio_account_id, display_name, account_type: account_type || "personal" });
    setMsg("Account linked.");
    reloadAccounts();
  });

  const doManualLink = wrap(async () => {
    await linkAccount({ zernio_account_id: manualId.trim(), display_name: manualName.trim() || null });
    setManualId("");
    setManualName("");
    setMsg("Account linked.");
    reloadAccounts();
  });

  const doUnlink = wrap(async (id) => {
    await unlinkAccount(id);
    reloadAccounts();
  });

  return (
    <>
      {error && <div className="error">{error}</div>}
      {msg && <div className="success">{msg}</div>}

      {usage && usage.ok && (
        <div className="card">
          <h2>Hub usage</h2>
          <UsageCard data={usage.data} />
        </div>
      )}

      <div className="card">
        <h2>AI Models Hub key</h2>
        <p className="muted">
          {user?.has_hub_key
            ? "A personal Hub key is set. Generation uses your key."
            : "No personal Hub key set — generation falls back to the server key (dev). Add yours for production."}
        </p>
        <label>Hub API key</label>
        <input
          value={hubKey}
          onChange={(e) => setHubKeyInput(e.target.value)}
          placeholder="amh_..."
        />
        <div className="row" style={{ marginTop: 10 }}>
          <button className="btn-primary" disabled={busy || !hubKey.trim()} onClick={saveHubKey}>
            Save key
          </button>
        </div>
      </div>

      <div className="card">
        <h2>Zernio key</h2>
        <p className="muted">
          {user?.has_zernio_key
            ? "Your Zernio key is set. You only see and post to LinkedIn accounts under your own Zernio connection."
            : "No Zernio key set. Add yours to find, link, and post to your LinkedIn accounts — each user only sees their own."}
        </p>
        <label>Zernio API key</label>
        <input
          value={zKey}
          onChange={(e) => setZKeyInput(e.target.value)}
          placeholder="sk_..."
        />
        <div className="row" style={{ marginTop: 10 }}>
          <button className="btn-primary" disabled={busy || !zKey.trim()} onClick={saveZernioKey}>
            Save key
          </button>
        </div>
      </div>

      <div className="card">
        <h2>Linked LinkedIn accounts</h2>
        {accounts.length === 0 ? (
          <div className="empty">No accounts linked yet.</div>
        ) : (
          <div className="pill-list">
            {accounts.map((a) => (
              <div className="pill" key={a.id}>
                <strong>{a.display_name || a.zernio_account_id}</strong>
                <span className="muted">({a.account_type})</span>
                <span className="badge published">{a.status}</span>
                <div className="spacer" />
                <button className="btn-danger" disabled={busy} onClick={() => doUnlink(a.id)}>
                  Unlink
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h2>Connect a new account</h2>
        <div className="row">
          <button className="btn-secondary" disabled={busy} onClick={findZernio}>
            Find accounts on Zernio
          </button>
        </div>
        {available && available.length > 0 && (
          <div className="pill-list" style={{ marginTop: 12 }}>
            {available.map((z, i) => {
              const id = z._id || z.id || z.accountId;
              const name = z.displayName || z.username || z.name || id;
              const type = (z.accountType || z.type) === "organization" ? "organization" : "personal";
              return (
                <div className="pill" key={id || i}>
                  <strong>{name}</strong>
                  <span className="muted">{id}</span>
                  <div className="spacer" />
                  <button className="btn-primary" disabled={busy} onClick={() => doLink(id, name, type)}>
                    Link
                  </button>
                </div>
              );
            })}
          </div>
        )}

        <h3 style={{ marginTop: 18 }}>Or link manually</h3>
        <label>Zernio account ID</label>
        <input value={manualId} onChange={(e) => setManualId(e.target.value)} placeholder="zacc_..." />
        <label>Display name (optional)</label>
        <input value={manualName} onChange={(e) => setManualName(e.target.value)} />
        <div className="row" style={{ marginTop: 10 }}>
          <button className="btn-primary" disabled={busy || !manualId.trim()} onClick={doManualLink}>
            Link account
          </button>
        </div>
      </div>
    </>
  );
}
