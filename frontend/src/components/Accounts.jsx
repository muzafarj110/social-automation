import { useEffect, useState } from "react";
import {
  listAccounts,
  zernioAvailable,
  linkAccount,
  unlinkAccount,
  setHubKey,
  setZernioKey,
} from "../api.js";

export default function Accounts({ user, accounts, reloadAccounts, refreshUser }) {
  const [available, setAvailable] = useState(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [hubKey, setHubKeyInput] = useState("");
  const [zKey, setZKeyInput] = useState("");
  const [manualId, setManualId] = useState("");
  const [manualName, setManualName] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    reloadAccounts();
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
