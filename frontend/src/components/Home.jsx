import { useEffect, useState } from "react";
import { listPosts, listInbox, listCampaigns, zernioMetrics, listAccounts, getBrand, listProactiveItems, generateProactiveItem, dismissProactiveItem } from "../api.js";
import HelpCenter from "./HelpCenter.jsx";
import { platformLabel, reachMetricLabel } from "../utils/platforms.js";
import { aggregatePosts, filterPostsByPlatform } from "../utils/analyticsAggregate.js";
import { hasFeature } from "../utils/features.js";

// ---- Agent identities (avatar + accent) used across the live work feed ----
const AGENTS = {
  content:    { name: "Content agent",      mono: "Co", bg: "#e1f5ee", fg: "#0F6E56" },
  autopilot:  { name: "Always-on Campaigns", mono: "AC", bg: "#e6f1fb", fg: "#185FA5" },
  approvals:  { name: "Approvals agent",    mono: "Ap", bg: "#faeeda", fg: "#854F0B" },
  competitor: { name: "Competitor agent",   mono: "Cp", bg: "#eeedfe", fg: "#534AB7" },
  leadgen:    { name: "Lead-gen agent",     mono: "Le", bg: "#fbeaf0", fg: "#993556" },
  listening:  { name: "Listening agent",    mono: "Li", bg: "#e6f5f2", fg: "#2a8c84" },
  seo:        { name: "SEO + GEO agent",    mono: "Se", bg: "#fff8e6", fg: "#7A5200" },
  whatsapp:   { name: "WhatsApp agent",     mono: "Wa", bg: "#dcfce7", fg: "#166534" },
};

// The team shown in the "working 24/7" status strip — filtered per-user below
// to only agents this account actually has (some are plan-gated).
const TEAM = ["content", "autopilot", "competitor", "leadgen", "listening", "seo"];
const AGENT_FEATURE = { leadgen: "lead_gen" };

const PROFILE_LEAD = {
  individual: "Brief your content agent on what to focus on this week.",
  influencer: "Brief your content agent — it'll plan across every platform.",
  startup: "Point your content agent at a goal — it'll generate and schedule the week.",
  company: "Brief your content agent once. It plans the rest of the week.",
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

export default function Home({ goTab, user, onDirective }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [directive, setDirective] = useState("");
  const [proactive, setProactive] = useState([]);
  const [helpOpen, setHelpOpen] = useState(false);
  const [metricsFilter, setMetricsFilter] = useState("all");

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
        let metrics = null, metricsPlatforms = [], metricsPosts = [];
        try {
          const z = await zernioMetrics();
          if (z.ok) {
            metrics = z.summary;
            metricsPlatforms = z.platforms || [];
            metricsPosts = z.data?.posts || [];
          }
        } catch { /* no key */ }
        setData({ posts, inbox, campaigns, accounts, brand, metrics, metricsPlatforms, metricsPosts });
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

  if (error) return <div className="error" role="alert">{error}</div>;
  if (!data) return <div className="empty">Loading your team…</div>;

  const scheduled = data.posts
    .filter((p) => p.status === "scheduled")
    .sort((a, b) => new Date(a.scheduled_for) - new Date(b.scheduled_for));
  const drafts = data.posts.filter((p) => p.status === "draft");
  const activeCampaigns = data.campaigns.filter((c) => c.status === "active");

  const connected = data.accounts.length > 0;
  const brandReady = !!(data.brand && (data.brand.voice || data.brand.brand_name));
  const hasCampaign = data.campaigns.length > 0;
  const liveTeam = TEAM.filter((k) => !AGENT_FEATURE[k] || hasFeature(user, AGENT_FEATURE[k]));
  const steps = [
    { done: connected, title: "Connect your channels", desc: "Link a social account so your agents can publish.", tab: "accounts", cta: "Connect" },
    { done: brandReady, title: "Brief your brand strategist", desc: "Set voice, audience and positioning — every agent uses it.", tab: "strategy", cta: "Set up brand" },
    { done: hasCampaign, title: "Activate Autopilot", desc: "Hand your team a goal and let them run 24/7.", tab: "campaigns", cta: "Activate" },
  ];
  const setupDone = steps.every((s) => s.done);
  const lead = PROFILE_LEAD[user?.profile_type] || "Brief your content agent on what to focus on this week.";

  const submitDirective = (e) => {
    e.preventDefault();
    const text = directive.trim();
    if (!text) return;
    if (onDirective) onDirective(text);
    else goTab("team");
  };

  const dismiss = async (id) => {
    setProactive((p) => p.filter((i) => i.id !== id));
    dismissProactiveItem(id).catch(() => {});
  };

  return (
    <>
      {/* Help modal overlay */}
      {helpOpen && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0,0,0,0.4)", zIndex: 999, display: "flex", alignItems: "center", justifyContent: "center",
          padding: 20,
        }} onClick={() => setHelpOpen(false)}>
          <div style={{
            background: "#fff", borderRadius: 12, maxWidth: 900, maxHeight: "90vh", overflow: "auto",
            width: "100%", boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
          }} onClick={(e) => e.stopPropagation()}>
            <div style={{ position: "sticky", top: 0, background: "#fff", borderBottom: "1px solid var(--line)", padding: "16px 28px", display: "flex", alignItems: "center", justifyContent: "space-between", zIndex: 10 }}>
              <h2 style={{ margin: 0, fontSize: 20 }}>How Autopilot Works</h2>
              <button onClick={() => setHelpOpen(false)} style={{ background: "none", border: "none", fontSize: 24, cursor: "pointer", color: "var(--muted)" }} aria-label="Close">×</button>
            </div>
            <div style={{ padding: 0 }}>
              <HelpCenter />
            </div>
          </div>
        </div>
      )}

      {/* Chat bar — briefs the Content agent's weekly plan in natural language */}
      <form onSubmit={submitDirective} style={{
        display: "flex", alignItems: "center", gap: 10, background: "#fff",
        border: "1px solid var(--line)", borderRadius: 999, padding: "8px 8px 8px 18px",
        boxShadow: "var(--shadow-sm)", marginBottom: 18,
      }}>
        <span style={{ color: "var(--teal)", fontSize: 18, lineHeight: 1 }}>✦</span>
        <input
          value={directive}
          onChange={(e) => setDirective(e.target.value)}
          placeholder="Tell your content agent what to focus on this week…"
          style={{ flex: 1, border: "none", padding: "8px 0", fontSize: 14.5, boxShadow: "none", background: "transparent" }}
        />
        <button type="submit" className="btn-primary" style={{ borderRadius: 999, width: 40, height: 40, padding: 0, fontSize: 18, flexShrink: 0 }} aria-label="Send to team">↑</button>
      </form>

      {/* Learn how it works button */}
      <div style={{ marginBottom: 18 }}>
        <button onClick={() => setHelpOpen(true)} style={{
          width: "100%", padding: "12px 16px", background: "var(--teal-tint)", border: "1px solid var(--teal)",
          borderRadius: 10, color: "var(--teal-deep)", fontSize: 13, fontWeight: 500, cursor: "pointer",
          textAlign: "center", transition: "all 0.2s",
        }} onMouseEnter={(e) => e.target.style.background = "var(--teal)"} onMouseEnter={(e) => { e.target.style.background = "var(--teal)"; e.target.style.color = "#fff"; }} onMouseLeave={(e) => { e.target.style.background = "var(--teal-tint)"; e.target.style.color = "var(--teal-deep)"; }}>
          📚 Learn how it works
        </button>
      </div>

      {/* Performance band (only when we have live metrics) */}
      {data.metrics && (() => {
        const platforms = data.metricsPlatforms || [];
        const shown = metricsFilter === "all"
          ? data.metrics
          : aggregatePosts(filterPostsByPlatform(data.metricsPosts || [], metricsFilter));
        const reachLabel = metricsFilter === "all" ? "Reach" : reachMetricLabel(metricsFilter);
        const reachValue = metricsFilter === "all"
          ? (shown.impressions || 0) + (shown.views || 0)
          : reachLabel === "Views" ? (shown.views || 0) : (shown.impressions || 0);
        return (
          <div className="hero" style={{ marginBottom: 18 }}>
            <div className="orb" />
            <div className="row" style={{ position: "relative", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
              <div>
                <h2 style={{ color: "#fff", margin: 0 }}>Account performance</h2>
                <p style={{ margin: "4px 0 0", opacity: 0.9, fontSize: 13 }}>
                  Real reach on your connected account(s) — includes anything posted there, not just what Autopilot made.
                </p>
              </div>
              <div className="spacer" />
              {platforms.length > 1 && (
                <select
                  aria-label="Filter performance by account"
                  value={metricsFilter}
                  onChange={(e) => setMetricsFilter(e.target.value)}
                  style={{ background: "#fff", color: "var(--teal-dark)", borderRadius: "var(--radius)", border: "none", padding: "9px 12px", fontSize: 13, fontWeight: 600 }}
                >
                  <option value="all">All accounts</option>
                  {platforms.map((p) => <option key={p} value={p}>{platformLabel(p)}</option>)}
                </select>
              )}
              <button className="btn-secondary" style={{ background: "#fff", color: "var(--teal-dark)" }}
                onClick={() => goTab("analytics")}>View analytics</button>
            </div>
            <div className="hero-metrics">
              <div><div className="hm-v">{reachValue.toLocaleString()}</div><div className="hm-l">{reachLabel}</div></div>
              <div><div className="hm-v">{(shown.total_likes || 0).toLocaleString()}</div><div className="hm-l">Total likes</div></div>
              <div><div className="hm-v">{(shown.post_count || 0).toLocaleString()}</div><div className="hm-l">Posts published</div></div>
              <div><div className="hm-v">{(shown.avg_likes || 0).toLocaleString()}</div><div className="hm-l">Avg likes / post</div></div>
            </div>
          </div>
        );
      })()}

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
        <h2 style={{ margin: 0 }}>Needs your attention</h2>
        <span className="muted" style={{ fontSize: 13 }}>
          {data.inbox.length > 0
            ? `${data.inbox.length} need your approval`
            : proactive.length > 0 ? `${proactive.length} update${proactive.length === 1 ? "" : "s"}` : "Nothing pending"}
        </span>
      </div>

      {data.inbox.length > 0 && (
        <FeedCard agent="approvals" tag="needs approval"
          primary={{ label: "Review & approve", onClick: () => goTab("inbox") }}>
          Drafted <strong>{data.inbox.length}</strong> repl{data.inbox.length === 1 ? "y" : "ies"} / outreach message{data.inbox.length === 1 ? "" : "s"} — waiting on your OK before they go out.
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

      {data.inbox.length === 0 && proactive.length === 0 && (
        <div className="empty" style={{ marginTop: 4, marginBottom: 18 }}>
          Nothing needs you right now.
        </div>
      )}

      <div className="row" style={{ marginTop: 24, marginBottom: 10, alignItems: "baseline" }}>
        <h2 style={{ margin: 0 }}>Team activity</h2>
      </div>

      {/* Agents working strip — only agents this account actually has */}
      <div className="card" style={{ marginBottom: 14, padding: "14px 18px" }}>
        <div className="row" style={{ alignItems: "center" }}>
          <div className="row" style={{ gap: 8, alignItems: "center" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--teal)", boxShadow: "0 0 0 4px rgba(54,173,163,0.16)" }} />
            <span style={{ fontWeight: 700, fontSize: 13.5 }}>{liveTeam.length} agent{liveTeam.length === 1 ? "" : "s"} working 24/7</span>
          </div>
          <div className="spacer" />
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {liveTeam.map((k) => (
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

      {scheduled.length === 0 && drafts.length === 0 && (
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
