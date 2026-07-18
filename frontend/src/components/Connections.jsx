import { useEffect, useState } from "react";
import {
  getConnections,
  connectTelegram,
  disconnectTelegram,
  toggleTelegramAutoPost,
  sendTelegram,
} from "../api.js";

const STEP_ICON = { done: "✓", active: "→" };

function StepNum({ n, state }) {
  const bg =
    state === "done"
      ? "var(--teal)"
      : state === "active"
      ? "var(--teal-light)"
      : "var(--light)";
  const color =
    state === "done"
      ? "#fff"
      : state === "active"
      ? "var(--teal-dark)"
      : "var(--muted)";
  const border = state === "active" ? "2px solid var(--teal)" : "1px solid var(--line)";
  return (
    <div
      style={{
        width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontWeight: 600, fontSize: 13, background: bg, color, border,
        marginTop: 2, position: "relative", zIndex: 1,
      }}
    >
      {state === "done" ? STEP_ICON.done : n}
    </div>
  );
}

function Step({ n, total, label, hint, state, children }) {
  const isLast = n === total;
  return (
    <div style={{ display: "flex", gap: 14, position: "relative" }}>
      {!isLast && (
        <div
          style={{
            position: "absolute", left: 15, top: 36, bottom: 0,
            width: 2, background: "var(--line)",
          }}
        />
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

function Input({ placeholder, type = "text", value, onChange }) {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        flex: 1, padding: "8px 12px", borderRadius: 8,
        border: "1px solid var(--line)", background: "var(--light)",
        fontSize: 13, color: "var(--ink)", fontFamily: "monospace", outline: "none",
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
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        ...styles[variant], padding: "8px 16px", borderRadius: 8,
        fontSize: 13, fontWeight: 500, cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.6 : 1,
      }}
    >
      {children}
    </button>
  );
}

function AutoToggle({ label, checked, onChange }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
      <div
        onClick={onChange}
        style={{
          width: 44, height: 24, borderRadius: 12, position: "relative",
          background: checked ? "var(--teal)" : "var(--line)", transition: "background 0.2s",
          cursor: "pointer",
        }}
      >
        <div
          style={{
            position: "absolute", top: 3, left: checked ? 23 : 3,
            width: 18, height: 18, borderRadius: "50%", background: "#fff",
            transition: "left 0.2s", boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
          }}
        />
      </div>
      <span style={{ fontSize: 13, color: "var(--ink)", fontWeight: 500 }}>{label}</span>
    </label>
  );
}

function ConnectedBadge({ name, sub, onDisconnect }) {
  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 12,
        background: "var(--light)", border: "1px solid var(--line)",
        borderRadius: 10, padding: "10px 14px", marginTop: 12,
      }}
    >
      <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#22c55e", flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: "var(--ink)" }}>{name}</div>
        {sub && <div style={{ fontSize: 12, color: "var(--muted)" }}>{sub}</div>}
      </div>
      <button
        onClick={onDisconnect}
        style={{
          fontSize: 12, color: "var(--muted)", background: "none", border: "none",
          cursor: "pointer", padding: "4px 8px", borderRadius: 6,
        }}
      >
        Disconnect
      </button>
    </div>
  );
}

function InfoBox({ children }) {
  return (
    <div
      style={{
        display: "flex", gap: 10, background: "var(--light)",
        border: "1px solid var(--line)", borderRadius: 10,
        padding: "10px 14px", fontSize: 12, color: "var(--muted)", lineHeight: 1.6, marginTop: 16,
      }}
    >
      <span style={{ color: "var(--teal)", flexShrink: 0, fontWeight: 600 }}>ℹ</span>
      <span>{children}</span>
    </div>
  );
}

// ── WhatsApp Panel ─────────────────────────────────────────────────────────────
// Full setup (connect, auto-reply AI, knowledge base, flagged conversations)
// now lives in the WhatsApp agent page — this is just a status summary + link.

function WhatsAppPanel({ status, goWhatsAppAgent }) {
  const connected = status?.connected;
  return (
    <div>
      <div style={{ fontSize: 16, fontWeight: 500, color: "var(--ink)", marginBottom: 4 }}>
        WhatsApp Business
      </div>
      <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 20 }}>
        Connection, the 24/7 auto-reply AI, and its knowledge base are managed in the WhatsApp agent —
        a dedicated AI agent, not just a settings toggle.
      </div>
      {connected ? (
        <div style={{
          display: "flex", alignItems: "center", gap: 12, background: "var(--light)",
          border: "1px solid var(--line)", borderRadius: 10, padding: "10px 14px",
        }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#22c55e", flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--ink)" }}>{status.verified_name || "WhatsApp Business"}</div>
            <div style={{ fontSize: 12, color: "var(--muted)" }}>{status.display_phone || status.to_number}</div>
          </div>
        </div>
      ) : (
        <div style={{
          display: "flex", alignItems: "center", gap: 12, background: "var(--light)",
          border: "1px solid var(--line)", borderRadius: 10, padding: "10px 14px",
        }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--muted)", flexShrink: 0 }} />
          <div style={{ fontSize: 13, color: "var(--muted)" }}>Not connected yet</div>
        </div>
      )}
      <div style={{ marginTop: 14 }}>
        <Btn onClick={goWhatsAppAgent}>
          {connected ? "Manage in WhatsApp agent →" : "Set up in WhatsApp agent →"}
        </Btn>
      </div>
    </div>
  );
}

// ── Telegram Panel ─────────────────────────────────────────────────────────────

function TelegramPanel({ status, onRefresh }) {
  const [botToken, setBotToken] = useState("");
  const [channelId, setChannelId] = useState("");
  const [sending, setSending] = useState(false);
  const [manualText, setManualText] = useState("");
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const connected = status?.connected;

  const connect = async () => {
    setErr(""); setMsg("");
    if (!botToken) { setErr("Enter your bot token."); return; }
    setSending(true);
    try {
      await connectTelegram({ bot_token: botToken, channel_id: channelId || null });
      setMsg("Connected! " + (channelId ? "Check your channel for a test message." : "Bot linked successfully."));
      setBotToken(""); setChannelId("");
      onRefresh();
    } catch (e) { setErr(e.message); }
    setSending(false);
  };

  const disconnect = async () => {
    if (!confirm("Disconnect Telegram?")) return;
    await disconnectTelegram();
    onRefresh();
  };

  const toggle = async () => {
    await toggleTelegramAutoPost();
    onRefresh();
  };

  const sendNow = async () => {
    if (!manualText) return;
    setSending(true); setErr(""); setMsg("");
    try {
      await sendTelegram({ text: manualText });
      setMsg("Message sent!"); setManualText("");
    } catch (e) { setErr(e.message); }
    setSending(false);
  };

  const stepState = (n) => {
    if (connected) return "done";
    return n === 2 ? "active" : n < 2 ? "done" : "pending";
  };

  return (
    <div>
      <div style={{ fontSize: 16, fontWeight: 500, color: "var(--ink)", marginBottom: 4 }}>
        Connect Telegram
      </div>
      <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 20 }}>
        Create a Telegram Bot — free, unlimited messages, 2 minute setup.
      </div>

      {connected ? (
        <>
          <ConnectedBadge
            name={status.bot_username || "Telegram Bot"}
            sub={status.channel_id ? `Channel: ${status.channel_id}` : "No channel set"}
            onDisconnect={disconnect}
          />
          <div style={{ marginTop: 14 }}>
            <AutoToggle
              label="Auto-post your content to Telegram"
              checked={status.auto_post}
              onChange={toggle}
            />
          </div>
          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--ink)", marginBottom: 6 }}>
              Send manual message
            </div>
            <textarea
              value={manualText}
              onChange={(e) => setManualText(e.target.value)}
              placeholder="Type a message to post to your channel..."
              rows={3}
              style={{
                width: "100%", padding: "8px 12px", borderRadius: 8,
                border: "1px solid var(--line)", background: "var(--light)",
                fontSize: 13, color: "var(--ink)", resize: "vertical", outline: "none",
                boxSizing: "border-box",
              }}
            />
            <div style={{ marginTop: 8 }}>
              <Btn onClick={sendNow} disabled={sending || !manualText}>
                {sending ? "Sending…" : "Post to channel"}
              </Btn>
            </div>
          </div>
        </>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          <Step n={1} total={4} label="Message @BotFather on Telegram" state={stepState(1)}
            hint='Open Telegram → search @BotFather → send /newbot → give your bot a name and username.'>
            <a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer"
              style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12,
                color: "var(--teal-dark)", textDecoration: "none", background: "var(--light)",
                border: "1px solid var(--teal)", borderRadius: 6, padding: "5px 12px" }}>
              Open Telegram ↗
            </a>
          </Step>
          <Step n={2} total={4} label="Copy your Bot Token" state={stepState(2)}
            hint="BotFather sends you a token like 7123456789:AAFxxxx — paste it below.">
            <div style={{ display: "flex", gap: 8 }}>
              <Input type="password" placeholder="7123456789:AAFxxxxxxxxxxxxxxxxxxxxxx"
                value={botToken} onChange={setBotToken} />
            </div>
          </Step>
          <Step n={3} total={4} label="Add bot as Admin to your Channel (optional)" state="pending"
            hint="Channel Settings → Administrators → Add Admin → search your bot. Needed to post to a channel.">
          </Step>
          <Step n={4} total={4} label="Enter your channel name" state="pending"
            hint="Your Telegram channel username (e.g. @YourChannel) or numeric ID. Leave blank to skip channel.">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Input placeholder="@YourChannel or -100123456789"
                value={channelId} onChange={setChannelId} />
              <Btn onClick={connect} disabled={sending}>
                {sending ? "Connecting…" : "Connect Telegram"}
              </Btn>
            </div>
          </Step>
        </div>
      )}

      {err && <div style={{ marginTop: 10, fontSize: 13, color: "#dc2626" }}>{err}</div>}
      {msg && <div style={{ marginTop: 10, fontSize: 13, color: "var(--teal-dark)" }}>{msg}</div>}

      <InfoBox>
        <strong>Completely free:</strong> Telegram Bot API is free with no rate limits for normal usage.
        Your bot can post to channels, groups, or individual users.
      </InfoBox>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

const PLATFORM_LABEL = {
  linkedin: "LinkedIn", twitter: "X", instagram: "Instagram", facebook: "Facebook",
  tiktok: "TikTok", youtube: "YouTube", pinterest: "Pinterest", reddit: "Reddit",
  bluesky: "Bluesky", threads: "Threads", googlebusiness: "Google Business",
  snapchat: "Snapchat", discord: "Discord",
};

export default function Connections({ accounts = [], goAccounts, goWhatsAppAgent }) {
  const [status, setStatus] = useState(null);
  const [tab, setTab] = useState("wa");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try { setStatus(await getConnections()); } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const wa = status?.whatsapp || {};
  const tg = status?.telegram || {};

  const channelCard = (id, emoji, name, desc, isConnected) => (
    <div
      key={id}
      onClick={() => setTab(id)}
      style={{
        background: "#fff", border: tab === id ? "2px solid var(--teal)" : "1px solid var(--line)",
        borderRadius: 12, padding: "1.1rem 1.25rem", cursor: "pointer",
        transition: "border-color 0.15s",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 12, fontSize: 22,
          display: "flex", alignItems: "center", justifyContent: "center",
          background: id === "wa" ? "#e7f7ef" : "#e6f3fb",
        }}>{emoji}</div>
        <div>
          <div style={{ fontWeight: 500, fontSize: 15, color: "var(--ink)" }}>{name}</div>
          <div style={{ fontSize: 12, color: "var(--muted)" }}>{desc}</div>
        </div>
        {isConnected && (
          <div style={{
            marginLeft: "auto", width: 8, height: 8, borderRadius: "50%", background: "#22c55e",
          }} />
        )}
      </div>
    </div>
  );

  return (
    <div style={{ maxWidth: 680 }}>
      <div style={{ background: "#fff", border: "1px solid var(--line)", borderRadius: 12, padding: "1.25rem 1.5rem", marginBottom: 24 }}>
        <div className="row" style={{ alignItems: "center", marginBottom: accounts.length ? 12 : 4 }}>
          <h2 style={{ margin: 0, fontSize: 15 }}>Connected accounts</h2>
          <div className="spacer" />
          <button className="btn-ghost" onClick={goAccounts} style={{ fontSize: 12, padding: "4px 10px" }}>
            Manage in Accounts →
          </button>
        </div>
        {accounts.length === 0 ? (
          <div className="muted" style={{ fontSize: 13 }}>
            No social accounts linked yet — LinkedIn, TikTok, Instagram, YouTube and others are
            connected under Accounts, not here.
          </div>
        ) : (
          <div className="pill-list">
            {accounts.map((a) => (
              <div className="pill" key={a.id}>
                <span className="badge kind">{PLATFORM_LABEL[a.platform] || a.platform}</span>
                <strong>{a.display_name || a.zernio_account_id}</strong>
                <span className="badge published">{a.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 20 }}>
        Connect messaging channels to cross-post content from any of your connected accounts, automatically or on demand.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }}>
        {channelCard("wa", "💬", "WhatsApp Business", "Broadcasts, outreach, sequences", wa.connected)}
        {channelCard("tg", "✈️", "Telegram", "Channel posts, community, newsletters", tg.connected)}
      </div>

      <div style={{ background: "#fff", border: "1px solid var(--line)", borderRadius: 12, padding: "1.5rem" }}>
        {loading ? (
          <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading…</div>
        ) : tab === "wa" ? (
          <WhatsAppPanel status={wa} goWhatsAppAgent={goWhatsAppAgent} />
        ) : (
          <TelegramPanel status={tg} onRefresh={load} />
        )}
      </div>
    </div>
  );
}
