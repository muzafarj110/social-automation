import { useEffect, useState } from "react";
import {
  getWhatsAppAgentSettings, updateWhatsAppAgentSettings,
  listWhatsAppFlagged, dismissWhatsAppFlagged,
  connectWhatsApp, disconnectWhatsApp,
  getBrand, saveBrand,
} from "../api.js";

// ── Small visual helpers (mirrors Connections.jsx's wizard chrome) ─────────────

const STEP_ICON = { done: "✓", active: "→" };

function StepNum({ n, state }) {
  const bg = state === "done" ? "var(--teal)" : state === "active" ? "var(--teal-light)" : "var(--light)";
  const color = state === "done" ? "#fff" : state === "active" ? "var(--teal-dark)" : "var(--muted)";
  const border = state === "active" ? "2px solid var(--teal)" : "1px solid var(--line)";
  return (
    <div style={{
      width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontWeight: 600, fontSize: 13, background: bg, color, border,
      marginTop: 2, position: "relative", zIndex: 1,
    }}>
      {state === "done" ? STEP_ICON.done : n}
    </div>
  );
}

function Step({ n, total, label, hint, state, children }) {
  const isLast = n === total;
  return (
    <div style={{ display: "flex", gap: 14, position: "relative" }}>
      {!isLast && (
        <div style={{ position: "absolute", left: 15, top: 36, bottom: 0, width: 2, background: "var(--line)" }} />
      )}
      <StepNum n={n} state={state} />
      <div style={{ paddingBottom: isLast ? 0 : 28, flex: 1 }}>
        <div style={{ fontWeight: 500, fontSize: 14, color: "var(--ink)", marginBottom: 4 }}>{label}</div>
        <div style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.55 }}>{hint}</div>
        {children && <div style={{ marginTop: 10 }}>{children}</div>}
      </div>
    </div>
  );
}

function Input({ placeholder, type = "text", value, onChange, monospace = true }) {
  return (
    <input
      type={type} placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)}
      style={{
        flex: 1, padding: "8px 12px", borderRadius: 8, border: "1px solid var(--line)",
        background: "var(--light)", fontSize: 13, color: "var(--ink)",
        fontFamily: monospace ? "monospace" : "inherit", outline: "none",
      }}
    />
  );
}

function Btn({ children, onClick, variant = "primary", disabled }) {
  const styles = {
    primary: { background: "var(--teal)", color: "#fff", border: "none" },
    ghost: { background: "var(--light)", color: "var(--ink)", border: "1px solid var(--line)" },
    danger: { background: "#fee2e2", color: "#b91c1c", border: "none" },
  };
  return (
    <button onClick={onClick} disabled={disabled} style={{
      ...styles[variant], padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500,
      cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.6 : 1,
    }}>
      {children}
    </button>
  );
}

function AutoToggle({ label, checked, onChange, disabled }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: disabled ? "default" : "pointer" }}>
      <div onClick={disabled ? undefined : onChange} style={{
        width: 44, height: 24, borderRadius: 12, position: "relative",
        background: checked ? "var(--teal)" : "var(--line)", transition: "background 0.2s",
        cursor: disabled ? "default" : "pointer", opacity: disabled ? 0.6 : 1,
      }}>
        <div style={{
          position: "absolute", top: 3, left: checked ? 23 : 3, width: 18, height: 18,
          borderRadius: "50%", background: "#fff", transition: "left 0.2s",
          boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
        }} />
      </div>
      <span style={{ fontSize: 13, color: "var(--ink)", fontWeight: 500 }}>{label}</span>
    </label>
  );
}

function CopyField({ label, value }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(value || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>{label}</div>
      <div style={{ display: "flex", gap: 8 }}>
        <Input value={value || ""} onChange={() => {}} />
        <Btn variant="ghost" onClick={copy}>{copied ? "Copied!" : "Copy"}</Btn>
      </div>
    </div>
  );
}

// ── Settings tab ────────────────────────────────────────────────────────────────

function SettingsTab({ settings, onRefresh }) {
  const [phoneId, setPhoneId] = useState("");
  const [token, setToken] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [toNumber, setToNumber] = useState("");
  const [keywords, setKeywords] = useState(settings?.escalation_keywords || "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const connected = settings?.connected;

  const connect = async () => {
    setErr(""); setMsg("");
    if (!phoneId || !token || !appSecret || !toNumber) { setErr("Fill in all fields."); return; }
    setBusy(true);
    try {
      await connectWhatsApp({
        phone_number_id: phoneId, access_token: token, app_secret: appSecret, to_number: toNumber,
      });
      setMsg("Connected! Now configure the webhook below so your AI can actually receive messages.");
      setPhoneId(""); setToken(""); setAppSecret(""); setToNumber("");
      onRefresh();
    } catch (e) { setErr(e.message); }
    setBusy(false);
  };

  const disconnect = async () => {
    if (!confirm("Disconnect WhatsApp? Your AI will stop replying to customers.")) return;
    await disconnectWhatsApp();
    onRefresh();
  };

  const toggleAutoReply = async () => {
    setBusy(true);
    try { await updateWhatsAppAgentSettings({ auto_reply_enabled: !settings.auto_reply_enabled }); onRefresh(); }
    catch (e) { setErr(e.message); }
    setBusy(false);
  };

  const saveKeywords = async () => {
    setBusy(true); setErr(""); setMsg("");
    try { await updateWhatsAppAgentSettings({ escalation_keywords: keywords }); setMsg("Saved."); onRefresh(); }
    catch (e) { setErr(e.message); }
    setBusy(false);
  };

  const stepState = (n) => (connected ? "done" : n === 3 ? "active" : n < 3 ? "done" : "pending");

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>WhatsApp connection</h2>
      <p className="muted" style={{ fontSize: 13 }}>
        Uses Meta's official WhatsApp Business Cloud API — free up to 1,000 conversations/month.
      </p>

      {connected ? (
        <div style={{
          display: "flex", alignItems: "center", gap: 12, background: "var(--light)",
          border: "1px solid var(--line)", borderRadius: 10, padding: "10px 14px", marginBottom: 16,
        }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#22c55e", flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{settings.verified_name || "WhatsApp Business"}</div>
            <div style={{ fontSize: 12, color: "var(--muted)" }}>{settings.display_phone || settings.to_number}</div>
          </div>
          <button onClick={disconnect} style={{
            fontSize: 12, color: "var(--muted)", background: "none", border: "none", cursor: "pointer",
          }}>Disconnect</button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 0, marginBottom: 16 }}>
          <div style={{
            display: "flex", gap: 10, background: "#fef3c7", border: "1px solid #f59e0b",
            borderRadius: 10, padding: "12px 14px", marginBottom: 20, fontSize: 13, color: "#92600e",
          }}>
            <span style={{ flexShrink: 0 }}>⚠️</span>
            <div>
              <strong>Heads up — this one's different.</strong> Unlike the one-click connect on the Accounts
              page, WhatsApp needs a one-time Meta Developer setup (~10-15 minutes): creating a free Meta app
              and copying a few IDs into the fields below. Worth doing in one sitting.
            </div>
          </div>
          <Step n={1} total={5} label="Create a Meta Developer App" state={stepState(1)}
            hint="Go to developers.facebook.com → My Apps → Create App → choose Business type.">
            <a href="https://developers.facebook.com/apps" target="_blank" rel="noopener noreferrer"
              style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12, color: "var(--teal-dark)",
                textDecoration: "none", background: "var(--light)", border: "1px solid var(--teal)",
                borderRadius: 6, padding: "5px 12px" }}>
              Open Meta Developers ↗
            </a>
          </Step>
          <Step n={2} total={5} label="Add WhatsApp product" state={stepState(2)}
            hint="Inside your app → Add Product → WhatsApp → Set Up." />
          <Step n={3} total={5} label="Copy Phone Number ID + App Secret" state="active"
            hint="WhatsApp → API Setup for the Phone Number ID. App Settings → Basic for the App Secret — this one signs incoming messages so no one else can trigger your AI.">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Input placeholder="Phone Number ID, e.g. 123456789012345" value={phoneId} onChange={setPhoneId} />
              <Input type="password" placeholder="App Secret" value={appSecret} onChange={setAppSecret} />
            </div>
          </Step>
          <Step n={4} total={5} label="Copy your Access Token" state="pending"
            hint="On the API Setup page, copy the Temporary Access Token. For production, use a permanent token from System Users.">
            <Input type="password" placeholder="EAAxxxxxxxxxxxxxxxx" value={token} onChange={setToken} />
          </Step>
          <Step n={5} total={5} label="Your WhatsApp Business number (E.164)" state="pending"
            hint="Example: +971501234567">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Input placeholder="+971501234567" value={toNumber} onChange={setToNumber} />
              <Btn onClick={connect} disabled={busy}>{busy ? "Connecting…" : "Connect WhatsApp"}</Btn>
            </div>
          </Step>
        </div>
      )}

      {err && <div className="error" role="alert" style={{ marginTop: 10 }}>{err}</div>}
      {msg && <div className="success" role="status" style={{ marginTop: 10 }}>{msg}</div>}

      {connected && (
        <>
          <div style={{ borderTop: "1px solid var(--line)", marginTop: 18, paddingTop: 18 }}>
            <div style={{ fontWeight: 500, fontSize: 14, marginBottom: 4 }}>Step 6 — Configure the webhook in Meta</div>
            <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
              In your Meta App → WhatsApp → Configuration, paste these into the Webhook fields and subscribe to
              the <code>messages</code> field. Without this, your AI never receives anything a customer sends.
            </p>
            <CopyField label="Callback URL" value={settings.webhook_url} />
            <CopyField label="Verify token" value={settings.webhook_verify_token} />
            <div style={{
              marginTop: 8, fontSize: 12, padding: "8px 12px", borderRadius: 8,
              background: settings.webhook_active ? "#dcfce7" : "#fef9c3",
              color: settings.webhook_active ? "#166534" : "#854d0e",
            }}>
              {settings.webhook_active
                ? "✓ Webhook is receiving messages."
                : "No message received yet — the webhook isn't configured correctly in Meta, or no customer has messaged you yet."}
            </div>
          </div>

          <div style={{ borderTop: "1px solid var(--line)", marginTop: 18, paddingTop: 18 }}>
            <AutoToggle
              label="AI replies 24/7 — no human review before sending"
              checked={settings.auto_reply_enabled}
              onChange={toggleAutoReply}
              disabled={busy}
            />
          </div>

          <div style={{ marginTop: 16 }}>
            <label>Escalation keywords <span className="muted">(flags a message for your review — doesn't block the reply)</span></label>
            <textarea value={keywords} onChange={(e) => setKeywords(e.target.value)}
              placeholder="refund, chargeback, cancel, complaint, legal, lawsuit, scam, fraud, credit card, bank details"
              style={{ minHeight: 60 }} />
            <div style={{ marginTop: 8 }}>
              <Btn variant="ghost" onClick={saveKeywords} disabled={busy}>Save keywords</Btn>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Knowledge base tab ───────────────────────────────────────────────────────────

function KnowledgeBaseTab() {
  const [entries, setEntries] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [form, setForm] = useState({ question: "", answer: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getBrand()
      .then((b) => setEntries(b?.docs?.faq?.entries || []))
      .catch(() => setEntries([]))
      .finally(() => setLoaded(true));
  }, []);

  const persist = async (next) => {
    setSaving(true); setError("");
    try {
      await saveBrand({ docs: { faq: { entries: next } } });
      setEntries(next);
    } catch (e) { setError(e.message); }
    setSaving(false);
  };

  const add = async (e) => {
    e.preventDefault();
    if (!form.question.trim() || !form.answer.trim()) return;
    await persist([...entries, { question: form.question.trim(), answer: form.answer.trim() }]);
    setForm({ question: "", answer: "" });
  };

  const remove = async (idx) => {
    await persist(entries.filter((_, i) => i !== idx));
  };

  if (!loaded) return <div className="empty">Loading…</div>;

  return (
    <>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Add a Q&amp;A entry</h2>
        <p className="muted" style={{ fontSize: 13 }}>
          Your AI only answers from what's here — pricing, policies, hours, anything customers commonly ask.
          If it's not covered, the AI says a team member will follow up instead of guessing.
        </p>
        <form onSubmit={add}>
          <label>Question</label>
          <input value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })}
            placeholder="Do you offer refunds?" required />
          <label style={{ marginTop: 10 }}>Answer</label>
          <textarea value={form.answer} onChange={(e) => setForm({ ...form, answer: e.target.value })}
            placeholder="Yes, full refunds within 30 days of purchase." style={{ minHeight: 70 }} required />
          {error && <div className="error" role="alert" style={{ marginTop: 10 }}>{error}</div>}
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn-primary" type="submit" disabled={saving}>
              {saving ? "Saving…" : "Add entry"}
            </button>
          </div>
        </form>
      </div>

      {entries.length === 0 ? (
        <div className="empty">No Q&amp;A entries yet. Add one above so your AI has something to answer from.</div>
      ) : (
        entries.map((item, idx) => (
          <div className="card" key={idx}>
            <div className="row" style={{ alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <h3 style={{ margin: "0 0 6px" }}>{item.question}</h3>
                <p className="muted" style={{ margin: 0, fontSize: 13 }}>{item.answer}</p>
              </div>
              <button className="btn-ghost" aria-label="Remove entry" disabled={saving} onClick={() => remove(idx)}>✕</button>
            </div>
          </div>
        ))
      )}
    </>
  );
}

// ── Flagged conversations tab ────────────────────────────────────────────────────

function FlaggedTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try { setItems(await listWhatsAppFlagged()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const dismiss = async (messageId) => {
    try { await dismissWhatsAppFlagged(messageId); setItems((cur) => cur.filter((i) => i.message.id !== messageId)); }
    catch (e) { setError(e.message); }
  };

  if (loading) return <div className="empty">Loading…</div>;

  return (
    <>
      {error && <div className="error" role="alert">{error}</div>}
      {items.length === 0 ? (
        <div className="empty">Nothing flagged — your AI hasn't hit any of your escalation keywords.</div>
      ) : (
        items.map(({ message, conversation, ai_reply }) => (
          <div className="card" key={message.id}>
            <div className="row">
              <span className="badge" style={{ background: "#fef9c3", color: "#854d0e" }}>
                Flagged: {message.flag_reason}
              </span>
              <span className="muted" style={{ fontSize: 12 }}>
                {conversation.customer_name || conversation.customer_phone}
              </span>
              <div className="spacer" />
              <button className="btn-ghost" onClick={() => dismiss(message.id)}>Dismiss</button>
            </div>
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 2 }}>Customer said</div>
              <div style={{ fontSize: 13 }}>{message.text}</div>
            </div>
            {ai_reply && (
              <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--line)" }}>
                <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 2 }}>Your AI replied</div>
                <div style={{ fontSize: 13 }}>{ai_reply.text}</div>
              </div>
            )}
          </div>
        ))
      )}
    </>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function WhatsAppAgent() {
  const [section, setSection] = useState("settings");
  const [settings, setSettings] = useState(null);
  const [loaded, setLoaded] = useState(false);

  const load = async () => {
    try { setSettings(await getWhatsAppAgentSettings()); }
    catch { setSettings({ connected: false }); }
    finally { setLoaded(true); }
  };
  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (loaded) setSection(settings?.connected ? "knowledge" : "settings");
  }, [loaded]); // eslint-disable-line

  if (!loaded) return <div className="empty">Loading…</div>;

  return (
    <div>
      <div className="filter-row" style={{ marginBottom: 16 }}>
        <button className={`filter-chip ${section === "settings" ? "active" : ""}`}
          onClick={() => setSection("settings")}>Settings</button>
        <button className={`filter-chip ${section === "knowledge" ? "active" : ""}`}
          disabled={!settings?.connected} onClick={() => setSection("knowledge")}>Knowledge base</button>
        <button className={`filter-chip ${section === "flagged" ? "active" : ""}`}
          disabled={!settings?.connected} onClick={() => setSection("flagged")}>Flagged conversations</button>
      </div>

      {section === "settings" && <SettingsTab settings={settings} onRefresh={load} />}
      {section === "knowledge" && settings?.connected && <KnowledgeBaseTab />}
      {section === "flagged" && settings?.connected && <FlaggedTab />}
    </div>
  );
}
