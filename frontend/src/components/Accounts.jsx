import { useEffect, useState } from "react";
import {
  listAccounts,
  zernioAvailable,
  connectUrl,
  linkAccount,
  unlinkAccount,
  setHubKey,
  setZernioKey,
  setAutomation,
  changePassword,
  getUsage,
  suppressAuthExpiry,
} from "../api.js";

// The platforms the app supports (mirrors backend app/core/platforms.py).
const PLATFORMS = [
  ["linkedin", "LinkedIn"], ["twitter", "X (Twitter)"], ["instagram", "Instagram"],
  ["facebook", "Facebook"], ["tiktok", "TikTok"], ["youtube", "YouTube"],
  ["pinterest", "Pinterest"], ["reddit", "Reddit"], ["bluesky", "Bluesky"],
  ["threads", "Threads"], ["googlebusiness", "Google Business"], ["telegram", "Telegram"],
  ["snapchat", "Snapchat"], ["whatsapp", "WhatsApp"], ["discord", "Discord"],
];
const PLATFORM_LABEL = Object.fromEntries(PLATFORMS);

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

  // Fallback: if the Hub's response doesn't match any known field, don't render
  // a blank card — show the raw scalar fields so usage is never "nothing".
  const known = [plan, name, email, today, total, limit, bonus].some((x) => x !== undefined);
  if (!known) {
    const rows = Object.entries(d).filter(([, v]) => v !== null && typeof v !== "object");
    if (!rows.length) return <p className="muted">No usage details available yet.</p>;
    return (
      <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
        {rows.map(([k, v]) => (
          <UsageTile key={k} label={k.replace(/_/g, " ")} value={fmt(v)} />
        ))}
      </div>
    );
  }

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

export default function Accounts({ user, accounts, reloadAccounts, refreshUser, goTab }) {
  const [available, setAvailable] = useState(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [hubKey, setHubKeyInput] = useState("");
  const [zKey, setZKeyInput] = useState("");
  const [manualId, setManualId] = useState("");
  const [manualName, setManualName] = useState("");
  const [manualPlatform, setManualPlatform] = useState("linkedin");
  const [busy, setBusy] = useState(false);
  const [usage, setUsage] = useState(null);
  const [showNextStep, setShowNextStep] = useState(false);

  useEffect(() => {
    reloadAccounts();
    getUsage().then(setUsage).catch(() => setUsage({ error: true }));
  }, []); // eslint-disable-line

  const wrap = (fn) => async (...a) => {
    setError("");
    setMsg("");
    setShowNextStep(false);
    setBusy(true);
    try {
      await fn(...a);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const toggleAutomation = wrap(async () => {
    await setAutomation(!user?.automation_paused);
    refreshUser();
  });

  const saveHubKey = wrap(async () => {
    await setHubKey(hubKey.trim());
    setHubKeyInput("");
    setMsg("Hub key saved.");
    refreshUser();
  });

  const saveZernioKey = wrap(async () => {
    await setZernioKey(zKey.trim());
    setZKeyInput("");
    setMsg("Channels connected.");
    refreshUser();
  });

  const findZernio = wrap(async () => {
    const res = await zernioAvailable();
    // Zernio response shape can vary; normalize to a list.
    const list = res?.accounts || res?.data || (Array.isArray(res) ? res : []);
    setAvailable(list);
    if (!list.length) setMsg("No connected accounts found yet.");
  });

  const doLink = wrap(async (zernio_account_id, display_name, account_type, platform) => {
    await linkAccount({
      zernio_account_id, display_name, platform: platform || "linkedin",
      account_type: account_type || "personal",
    });
    setMsg("Account linked.");
    if (accounts.length === 0) setShowNextStep(true);
    reloadAccounts();
  });

  const [connectPlatform, setConnectPlatform] = useState("linkedin");
  // No hash here: Zernio appends "?connected=…&accountId=…" to this URL, and a
  // "#accounts" suffix would put those query params inside the hash instead of
  // the query string (the browser parses "path#accounts?x=1" as hash
  // "accounts?x=1", search ""), so the OAuth-return detection below never saw it.
  const returnUrl = (typeof window !== "undefined")
    ? window.location.origin + window.location.pathname : "";
  const doConnect = wrap(async () => {
    const res = await connectUrl(connectPlatform, returnUrl);
    if (res?.auth_url) window.location.href = res.auth_url; // full-page; returns here after auth
  });

  // Pull this customer's connected accounts and link any not already linked.
  const doImport = wrap(async () => {
    const res = await zernioAvailable();
    const list = res?.accounts || res?.data || (Array.isArray(res) ? res : []);
    setAvailable(list);
    const have = new Set(accounts.map((a) => a.zernio_account_id));
    let linked = 0;
    for (const z of list) {
      const id = z._id || z.id || z.accountId;
      if (id && !have.has(id)) {
        const platform = (z.platform || "linkedin").toLowerCase();
        const name = z.displayName || z.username || z.name || id;
        const type = (z.accountType || z.type) === "organization" ? "organization" : "personal";
        try { await linkAccount({ zernio_account_id: id, display_name: name, platform, account_type: type }); linked++; } catch { /* skip */ }
      }
    }
    if (linked) {
      setMsg(`Imported ${linked} account${linked === 1 ? "" : "s"}.`);
      if (accounts.length === 0) setShowNextStep(true);
      reloadAccounts();
    }
    else if (!list.length) setMsg("No connected accounts found yet — click Connect above.");
  });

  // When the user returns from the platform's OAuth (?connected=…), auto-import.
  useEffect(() => {
    if (typeof window !== "undefined" && /[?&]connected=/.test(window.location.search)) {
      // Keep the user right here on the Accounts page through the import — a
      // transient 401 must not bounce them to the auth screen (suppress flag),
      // and doImport() itself reloads the list so the new account shows up.
      suppressAuthExpiry(true);
      (async () => {
        try {
          await doImport();
        } catch (e) {
          setError(e.message || "Couldn't import the connected account — click \"Refresh connected accounts\" to try again.");
        } finally {
          suppressAuthExpiry(false);
          window.history.replaceState({}, "", window.location.origin + window.location.pathname + "#accounts");
        }
      })();
    }
  }, []); // eslint-disable-line

  const doManualLink = wrap(async () => {
    await linkAccount({
      zernio_account_id: manualId.trim(), display_name: manualName.trim() || null,
      platform: manualPlatform,
    });
    setManualId("");
    setManualName("");
    setMsg("Account linked.");
    if (accounts.length === 0) setShowNextStep(true);
    reloadAccounts();
  });

  const doUnlink = wrap(async (id) => {
    await unlinkAccount(id);
    reloadAccounts();
  });

  const [curPw, setCurPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const doChangePassword = wrap(async () => {
    await changePassword(curPw, newPw);
    setCurPw(""); setNewPw("");
    setMsg("Password updated.");
  });

  return (
    <>
      {error && <div className="flash error" role="alert">{error}</div>}
      {msg && (
        <div className="flash success" role="status">
          {msg}
          {showNextStep && goTab && (
            <> · <button className="btn-ghost btn-compact" onClick={() => goTab("strategy")}>
              Next: brief your brand strategist →
            </button></>
          )}
        </div>
      )}

      <div className="card" style={user?.automation_paused ? { borderLeft: "4px solid #d97706" } : undefined}>
        <div className="row" style={{ alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0 }}>Automation {user?.automation_paused ? "is paused" : "is on"}</h2>
            <p className="muted" style={{ margin: "4px 0 0" }}>
              {user?.automation_paused
                ? "Nothing publishes automatically — every campaign post is saved as a draft for you to approve."
                : "Auto-mode campaigns publish on schedule. Pause anytime to hold everything for review."}
            </p>
          </div>
          <div className="spacer" />
          <button className={user?.automation_paused ? "btn-primary" : "btn-danger"}
            disabled={busy} onClick={toggleAutomation}>
            {user?.automation_paused ? "Resume automation" : "Pause all automation"}
          </button>
        </div>
      </div>

      <div className="card">
        <h2>AI usage</h2>
        {!usage
          ? <p className="muted">Loading usage…</p>
          : usage.error
            ? <p className="muted">Couldn't load AI usage right now. Your credits still show in the sidebar.</p>
            : usage.managed
              ? (
                <p className="muted">
                  Your AI runs on Autopilot's managed capacity — no setup needed.
                  {" "}You have <strong>{user?.credits ?? 0}</strong> credits remaining.
                </p>
              )
              : <UsageCard data={usage.data} />}
      </div>

      <div className="card">
        <h2>Linked social accounts</h2>
        {accounts.length === 0 ? (
          <div className="empty">No accounts linked yet.</div>
        ) : (
          <div className="pill-list">
            {accounts.map((a) => (
              <div className="pill" key={a.id}>
                <span className="badge kind">{PLATFORM_LABEL[a.platform] || a.platform}</span>
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
        <p className="muted">Pick a platform and click Connect. You sign in on the platform itself — no keys, no copying IDs — then you're brought right back here.</p>
        <div className="row" style={{ alignItems: "flex-end", flexWrap: "wrap" }}>
          <div>
            <label htmlFor="acct-platform">Platform</label>
            <select id="acct-platform" value={connectPlatform} onChange={(e) => setConnectPlatform(e.target.value)}>
              {PLATFORMS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <button className="btn-primary" disabled={busy} onClick={doConnect}>
            Connect {PLATFORM_LABEL[connectPlatform] || connectPlatform}
          </button>
          <button className="btn-secondary" disabled={busy} onClick={doImport}>
            Refresh connected accounts
          </button>
        </div>
        {available && available.length > 0 && (
          <div className="pill-list" style={{ marginTop: 12 }}>
            {available.map((z, i) => {
              const id = z._id || z.id || z.accountId;
              const name = z.displayName || z.username || z.name || id;
              const type = (z.accountType || z.type) === "organization" ? "organization" : "personal";
              const platform = (z.platform || "linkedin").toLowerCase();
              const linked = accounts.some((a) => a.zernio_account_id === id);
              return (
                <div className="pill" key={id || i}>
                  <span className="badge kind">{PLATFORM_LABEL[platform] || platform}</span>
                  <strong>{name}</strong>
                  <div className="spacer" />
                  {linked
                    ? <span className="badge published">Linked</span>
                    : <button className="btn-primary" disabled={busy} onClick={() => doLink(id, name, type, platform)}>Link</button>}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
