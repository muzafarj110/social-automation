import { useEffect, useState } from "react";
import { listPosts, listInbox, listCampaigns, zernioMetrics, listAccounts, getBrand, listProactiveItems, generateProactiveItem, dismissProactiveItem } from "../api.js";

// ---- Agent identities (avatar + accent) used across the live work feed ----
const AGENTS = {
  content:    { name: "Content agent",      mono: "Co", bg: "#e1f5ee", fg: "#0F6E56" },
  autopilot:  { name: "Autopilot agent",    mono: "Au", bg: "#e6f1fb", fg: "#185FA5" },
  approvals:  { name: "Approvals agent",    mono: "Ap", bg: "#faeeda", fg: "#854F0B" },
  competitor: { name: "Competitor agent",   mono: "Cp", bg: "#eeedfe", fg: "#534AB7" },
  leadgen:    { name: "Lead-gen agent",     mono: "Le", bg: "#fbeaf0", fg: "#993556" },
  listening:  { name: "Listening agent",    mono: "Li", bg: "#e6f5f2", fg: "#2a8c84" },
  seo:        { name: "SEO + GEO agent",    mono: "Se", bg: "#fff8e6", fg: "#7A5200" },
};

// The team shown in the "working 24/7" status strip.
const TEAM = ["content", "autopilot", "competitor", "leadgen", "listening", "seo"];

const PROFILE_LEAD = {
  individual: "Tell your team what to focus on and they'll take it from here.",
  influencer: "Direct your content engine across every platform.",
  startup: "Point your team at a goal — they'll generate, schedule and engage.",
  company: "Brief your AI marketing team once. They run the rest.",
};

function Avatar({ agent }) {
  const a = AGENTS[agent];
  return (
    <span style={{
      width: 32, height: 32, borderRadius: 9, flexShrink: 0, display: "grid", placeItems: "center",
      background: a.bg, color: a.fg, fontWeight: 700, fontSize: 12,
    }}>{a.mono}</span>
  );
}

function FeedCard({ agent, when, children, primary, secondary, tag }) {
  const a = AGENTS[agent];
  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div className="row" style={{ alignItems: "center", flexWrap: "nowrap", gap: 11 }}>
        <Avatar agent={agent} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontSize: 12, color: "var(--muted)" }}>
            <strong style={{ color: a.fg, fontWeight: 700 }}>{a.name}</strong>
          </div>
          <div style={{ fontSize: 14.5, color: "var(--ink)", marginTop: 2, lineHeight: 1.5 }}>{children}</div>
        </div>
        {tag && <span className="badge pending" style={{ flexShrink: 0 }}>{tag}</span>}
        {when && <span className="muted" style={{ fontSize: 11.5, flexShrink: 0, whiteSpace: "nowrap" }}>{when}</span>}
      </div>
      {(primary || secondary) && (
        <div className="row" style={{ marginTop: 12, marginLeft: 43 }}>
          {primary && <button className="btn-primary" style={{ fontSize: 13, padding: "8px 16px" }} onClick={primary.onClick}>{primary.label}</button>}
          {secondary && <button className="btn-secondary" style={{ fontSize: 13, padding: "8px 14px" }} onClick={secondary.onClick}>{secondary.label}</button>}
        </div>
      )}
    </div>
  );
}

function ago(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const mins = Math.round((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return d.toLocaleDateString();
}

export default function Home({ goTab, user }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [directive, setDirective] = useState("");
  const [proactive, setProactive] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const [posts, inbox, campaigns, accounts, brand] = await Promise.all([
          listPosts().catch(() => []),
          listInbox("pending").catch(() => []),
          listCampaigns().catch(() => []),
          listAccounts().catch(() => []),
          getBrand().catch(() => ({})),
        ]);
        let metrics = null;
        try { const z = await zernioMetrics(); if (z.ok) metrics = z.summary; } catch { /* no key */ }
        setData({ posts, inbox, campaigns, accounts, brand, metrics });
      } catch (e) { setError(e.message); }
    })();
  }, []);

  // Load proactive items; if none exist yet, trigger generation so the feed
  // isn't empty on first visit.
  useEffect(() => {
    (async () => {
      try {
        let items = await listProactiveItems().catch(() => []);
        if (items.length === 0) {
          const fresh = await generateProactiveItem().catch(() => null);
          if (fresh) items = [fresh];
        }
        setProactive(items);
      } catch { /* non-critical */ }
    })();
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <div className="empty">Loading your team…</div>;

  const scheduled = data.posts
    .filter((p) => p.status === "scheduled")
    .sort((a, b) => new Date(a.scheduled_for) - new Date(b.scheduled_for));
  const drafts = data.posts.filter((p) => p.status === "draft");
  const activeCampaigns = data.campaigns.filter((c) => c.status === "active");

  const connected = data.accounts.length > 0;
  const brandReady = !!(data.brand && (data.brand.voice || data.brand.brand_name));
  const hasCampaign = data.campaigns.length > 0;
  const steps = [
    { done: connected, title: "Connect your channels", desc: "Link a social account so your agents can publish.", tab: "accounts", cta: "Connect" },
    { done: brandReady, title: "Brief your brand strategist", desc: "Set voice, audience and positioning — every agent uses it.", tab: "strategy", cta: "Set up brand" },
    { done: hasCampaign, title: "Activate Autopilot", desc: "Hand your team a goal and let them run 24/7.", tab: "campaigns", cta: "Activate" },
  ];
  const setupDone = steps.every((s) => s.done);
  const lead = PROFILE_LEAD[user?.profile_type] || "Tell your team what to focus on. They take it from here.";

  const submitDirective = (e) => {
    e.preventDefault();
    if (directive.trim()) goTab("team");
  };

  const dismiss = async (id) => {
    setProactive((p) => p.filter((i) => i.id !== id));
    dismissProactiveItem(id).catch(() => {});
  };

  return (
    <>
      {/* Chat bar — direct the whole team in natural language */}
      <form onSubmit={submitDirective} style={{
        display: "flex", alignItems: "center", gap: 10, background: "#fff",
        border: "1px solid var(--line)", borderRadius: 999, padding: "8px 8px 8px 18px",
        boxShadow: "var(--shadow-sm)", marginBottom: 18,
      }}>
        <span style={{ color: "var(--teal)", fontSize: 18, lineHeight: 1 }}>✦</span>
        <input
          value={directive}
          onChange={(e) => setDirective(e.target.value)}
          placeholder="Tell your team what to focus on this week…"
          style={{ flex: 1, border: "none", padding: "8px 0", fontSize: 14.5, boxShadow: "none", background: "transparent" }}
        />
        <button type="submit" className="btn-primary" style={{ borderRadius: 999, width: 40, height: 40, padding: 0, fontSize: 18, flexShrink: 0 }} aria-label="Send to team">↑</button>
      </form>

      {/* Agents working strip */}
      <div className="card" style={{ marginBottom: 18, padding: "14px 18px" }}>
        <div className="row" style={{ alignItems: "center" }}>
          <div className="row" style={{ gap: 8, alignItems: "center" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--teal)", boxShadow: "0 0 0 4px rgba(54,173,163,0.16)" }} />
            <span style={{ fontWeight: 700, fontSize: 13.5 }}>{TEAM.length} agents working 24/7</span>
          </div>
          <div className="spacer" />
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {TEAM.map((k) => (
              <span key={k} title={AGENTS[k].name} style={{
                display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12,
                background: AGENTS[k].bg, color: AGENTS[k].fg, padding: "4px 10px", borderRadius: 999, fontWeight: 600,
              }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "currentColor" }} />
                {AGENTS[k].name.replace(" agent", "")}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Performance band (only when we have live metrics) */}
      {data.metrics && (
        <div className="hero" style={{ marginBottom: 18 }}>
          <div className="orb" />
          <div className="row" style={{ position: "relative", alignItems: "center" }}>
            <div>
              <h2 style={{ color: "#fff", margin: 0 }}>Your performance</h2>
              <p style={{ margin: "4px 0 0", opacity: 0.9, fontSize: 13 }}>What your AI team has driven so far</p>
            </div>
            <div className="spacer" />
            <button className="btn-secondary" style={{ background: "#fff", color: "var(--teal-dark)" }}
              onClick={() => goTab("analytics")}>View analytics</button>
          </div>
          <div className="hero-metrics">
            <div><div className="hm-v">{(data.metrics.impressions || 0).toLocaleString()}</div><div className="hm-l">Impressions</div></div>
            <div><div className="hm-v">{(data.metrics.total_likes || 0).toLocaleString()}</div><div className="hm-l">Total likes</div></div>
            <div><div className="hm-v">{(data.metrics.post_count || 0).toLocaleString()}</div><div className="hm-l">Posts published</div></div>
            <div><div className="hm-v">{(data.metrics.avg_likes || 0).toLocaleString()}</div><div className="hm-l">Avg likes / post</div></div>
          </div>
        </div>
      )}

      {/* Setup steps — only until the team is fully briefed */}
      {!setupDone && (
        <div className="card" style={{ marginBottom: 18 }}>
          <h2>Get your team set up</h2>
          <p className="muted" style={{ marginTop: -6 }}>{lead}</p>
          <div className="pill-list" style={{ marginTop: 10 }}>
            {steps.map((s, i) => (
              <div className="pill" key={i} style={{ alignItems: "center" }}>
                <span style={{
                  width: 24, height: 24, borderRadius: "50%", display: "grid", placeItems: "center",
                  fontSize: 13, fontWeight: 700, flexShrink: 0,
                  background: s.done ? "#dcfce7" : "var(--light)", color: s.done ? "#166534" : "var(--teal-dark)",
                }}>{s.done ? "✓" : i + 1}</span>
                <div>
                  <div style={{ fontWeight: 600, color: "var(--ink)" }}>{s.title}</div>
                  <div className="muted" style={{ fontSize: 13 }}>{s.desc}</div>
                </div>
                <div className="spacer" />
                {s.done
                  ? <span className="badge published">Done</span>
                  : <button className="btn-primary" onClick={() => goTab(s.tab)}>{s.cta}</button>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ---- Live work feed ---- */}
      <div className="row" style={{ marginBottom: 10, alignItems: "baseline" }}>
        <h2 style={{ margin: 0 }}>Live work feed</h2>
        <span className="muted" style={{ fontSize: 13 }}>
          {data.inbox.length > 0 ? `${data.inbox.length} need your approval` : "Up to date"}
        </span>
      </div>

      {data.inbox.length > 0 && (
        <FeedCard agent="approvals" tag="needs approval"
          primary={{ label: "Review & approve", onClick: () => goTab("inbox") }}>
          Drafted <strong>{data.inbox.length}</strong> repl{data.inbox.length === 1 ? "y" : "ies"} / outreach message{data.inbox.length === 1 ? "" : "s"} — waiting on your OK before they go out.
        </FeedCard>
      )}

      {scheduled.slice(0, 3).map((p) => (
        <FeedCard key={p.id} agent="autopilot" when={p.scheduled_for ? new Date(p.scheduled_for).toLocaleString() : ""}
          primary={{ label: "Open", onClick: () => goTab("posts") }}
          secondary={{ label: "Calendar", onClick: () => goTab("calendar") }}>
          Scheduled a post: “{p.body.slice(0, 120)}{p.body.length > 120 ? "…" : ""}”
        </FeedCard>
      ))}

      {drafts.length > 0 && (
        <FeedCard agent="content"
          primary={{ label: "Review drafts", onClick: () => goTab("posts") }}>
          Wrote <strong>{drafts.length}</strong> new draft{drafts.length === 1 ? "" : "s"} ready to schedule or publish.
        </FeedCard>
      )}

      {/* Proactive agent items — auto-generated by the background scheduler */}
      {proactive.map((item) => {
        const agentKey = AGENTS[item.agent] ? item.agent : "content";
        return (
          <FeedCard key={item.id} agent={agentKey} tag="auto"
            when={item.generated_at ? ago(item.generated_at) : ""}
            primary={item.action_tab
              ? { label: `Open ${AGENTS[agentKey]?.name || "agent"}`, onClick: () => goTab(item.action_tab) }
              : undefined}
            secondary={{ label: "Dismiss", onClick: () => dismiss(item.id) }}>
            <strong style={{ display: "block", marginBottom: 3 }}>{item.title}</strong>
            {item.body}
          </FeedCard>
        );
      })}

      {scheduled.length === 0 && drafts.length === 0 && data.inbox.length === 0 && (
        <div className="empty" style={{ marginTop: 4 }}>
          {hasCampaign
            ? "Your team is warming up — fresh work will appear here shortly."
            : "Activate Autopilot and your team will start filling this feed on their own."}
        </div>
      )}

      <div className="row" style={{ marginTop: 6 }}>
        <span className="muted" style={{ fontSize: 12.5 }}>
          {activeCampaigns.length} active campaign{activeCampaigns.length === 1 ? "" : "s"} · {scheduled.length} scheduled · {drafts.length} draft{drafts.length === 1 ? "" : "s"}
        </span>
      </div>
    </>
  );
}
