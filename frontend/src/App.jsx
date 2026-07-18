import { useEffect, useRef, useState } from "react";
import { getToken, logout, me, listAccounts, listClients, createClient, activateClient, deactivateClient } from "./api.js";
import { hasFeature } from "./utils/features.js";
import Auth from "./components/Auth.jsx";
import Landing from "./components/Landing.jsx";
import Onboarding from "./components/Onboarding.jsx";
import Home from "./components/Home.jsx";
import Strategy from "./components/Strategy.jsx";
import Accounts from "./components/Accounts.jsx";
import Posts from "./components/Posts.jsx";
import Inbox from "./components/Inbox.jsx";
import Campaigns from "./components/Campaigns.jsx";
import Analytics from "./components/Analytics.jsx";
import ProfileStudio from "./components/ProfileStudio.jsx";
import Admin from "./components/Admin.jsx";
import Billing from "./components/Billing.jsx";
import Calendar from "./components/Calendar.jsx";
import Leads from "./components/Leads.jsx";
import Opportunities from "./components/Opportunities.jsx";
import Studio from "./components/Studio.jsx";
import VideoAgent from "./components/VideoAgent.jsx";
import WhatsAppAgent from "./components/WhatsAppAgent.jsx";
import ContentTeam from "./components/ContentTeam.jsx";
import Competitor from "./components/Competitor.jsx";
import SocialListening from "./components/SocialListening.jsx";
import SeoGeo from "./components/SeoGeo.jsx";
import Connections from "./components/Connections.jsx";
import HelpCenter from "./components/HelpCenter.jsx";

// Each item: [tabId, label, featureFlag, working?]. `working` shows a live
// pulsing status dot — the "this agent is on the job 24/7" cue (NoimosAI model).
const NAV = [
  { group: "Command center", items: [["home", "Live work feed", null]] },
  { group: "Your AI team", items: [
    ["team", "Content agent", null, true],
    ["campaigns", "Always-on Campaigns", "autopilot", true],
    ["strategy", "Brand strategist", "strategy", false],
    ["studio", "Studio agent", null, false],
    ["videoagent", "Video agent", null, false],
    ["whatsappagent", "WhatsApp agent", null, false],
  ] },
  { group: "Growth agents", items: [
    ["competitor", "Competitor agent", null, true],
    ["listening", "Social listening", null, true],
    ["seo", "SEO + GEO agent", null, true],
    ["opportunities", "Opportunities", null, true],
    ["leads", "Lead-gen agent", null, true],
    ["profile", "Profile optimizer", "profile_studio", false],
    ["analytics", "Growth analytics", "analytics", false],
  ] },
  { group: "Workspace", items: [["calendar", "Calendar", null], ["posts", "Posts", null], ["inbox", "Approvals", "inbox"]] },
  { group: "Settings", items: [["accounts", "Accounts", null], ["connections", "Messaging channels", null], ["billing", "Billing", null]] },
];
// Admin-only nav group, appended when the user is an operator.
const ADMIN_NAV = { group: "Admin", items: [["admin", "Users", null]] };
const TITLES = {
  home: ["Live work feed", "What your AI marketing team is doing right now"],
  team: ["Content agent", "One post now, or a week of drafts — you approve once"],
  strategy: ["Brand strategist", "Your voice, persona and positioning — used by every agent"],
  studio: ["Studio agent", "Reports, email, SEO, formats & graphics — powered by AI"],
  videoagent: ["Video agent", "Turn a topic into a short + long video, ready to post"],
  whatsappagent: ["WhatsApp agent", "A 24/7 AI that answers customer messages from your knowledge base"],
  campaigns: ["Always-on Campaigns", "Set it once — AI writes, tailors and posts on a schedule"],
  posts: ["Posts", "Drafts, scheduled and published"],
  inbox: ["Approvals", "AI-drafted replies, DMs and outreach to approve"],
  profile: ["Profile optimizer", "Optimize your professional profile"],
  analytics: ["Growth analytics", "Performance and AI strategy"],
  calendar: ["Calendar", "Everything going out, across every platform"],
  competitor: ["Competitor agent", "Track rivals — AI surfaces tactics to copy and gaps to win"],
  listening: ["Social listening", "Monitor conversations — find high-intent prospects before they find you"],
  seo: ["SEO + GEO agent", "Rank on search and get cited in ChatGPT, Perplexity and Claude"],
  opportunities: ["Opportunities", "What to act on next, from your own data"],
  leads: ["Lead-gen agent", "Capture leads and let AI draft outreach"],
  accounts: ["Accounts", "Keys, connected accounts and usage"],
  connections: ["Messaging channels", "Connect WhatsApp Business and Telegram for cross-channel posting"],
  billing: ["Billing", "Your credits and top-ups"],
  admin: ["Users", "Manage plans, access and account status"],
  help: ["How Autopilot Works", "Learn how to generate leads, create content, and automate your marketing"],
};

// Only a real password-reset / email-verify link should force the auth screen.
// Must scope to those flows (`#reset`/`#verify`) — a bare /token=/ also matches
// OAuth-callback params like `oauth_token=` (LinkedIn/Twitter) and would wrongly
// bounce a logged-in user to the auth screen when they return from connecting a
// social account. Mirrors Auth.jsx's readToken() scoping.
function isResetVerifyLink(str) {
  return /[?&]token=/.test(str) && /(reset|verify)/i.test(str);
}

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()));
  // null = show public landing page; "login"/"register" = show the auth screen.
  // Jump straight to auth when a reset/verify link is opened (has ?token=).
  const [authView, setAuthView] = useState(() => {
    const h = (window.location.hash || "") + (window.location.search || "");
    return isResetVerifyLink(h) ? "login" : null;
  });
  const [user, setUser] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [tab, setTab] = useState("home");
  const [teamBrief, setTeamBrief] = useState("");
  const [postsRefresh, setPostsRefresh] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [welcomeToast, setWelcomeToast] = useState(null);
  const sidebarRef = useRef(null);
  const menuBtnRef = useRef(null);
  const prevMenuOpen = useRef(false);

  const refreshUser = async () => {
    try { setUser(await me()); }
    catch { logout(); setAuthed(false); }
  };
  const reloadAccounts = async () => {
    try { setAccounts(await listAccounts()); } catch { /* ignore */ }
  };
  const [clients, setClients] = useState([]);
  const loadClients = async () => {
    try { const r = await listClients(); setClients(r.clients || []); } catch { /* ignore */ }
  };
  const switchClient = async (val) => {
    try {
      if (val === "self") await deactivateClient(); else await activateClient(Number(val));
      await refreshUser(); await reloadAccounts();
    } catch { /* ignore */ }
  };
  const addClient = async () => {
    const name = window.prompt("New client name?");
    if (!name || !name.trim()) return;
    try { await createClient(name.trim()); await refreshUser(); await loadClients(); } catch { /* ignore */ }
  };

  useEffect(() => {
    if (authed) { refreshUser(); reloadAccounts(); loadClients(); }
  }, [authed]); // eslint-disable-line

  // When any request gets a 401 (token expired after ~1h), drop straight to the
  // login screen rather than showing a logged-in shell with empty data.
  useEffect(() => {
    const onExpired = () => { logout(); setAuthed(false); setUser(null); setAccounts([]); setAuthView("login"); };
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, []);

  // Close the mobile drawer with Escape.
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e) => { if (e.key === "Escape") setMenuOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  // Move focus into the drawer when it opens, and back to the hamburger
  // button when it closes (skip on initial mount before it's ever opened).
  useEffect(() => {
    if (menuOpen) {
      const el = sidebarRef.current?.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      el?.focus();
    } else if (prevMenuOpen.current) {
      menuBtnRef.current?.focus();
    }
    prevMenuOpen.current = menuOpen;
  }, [menuOpen]);

  // Show a one-time welcome toast right after a fresh registration (Auth.jsx
  // sets this sessionStorage key just before calling onAuthed()). Depends on
  // "authed" (not just []) since registration flips that state without
  // remounting App — a mount-only effect would miss it.
  useEffect(() => {
    if (!authed) return;
    const msg = sessionStorage.getItem("welcomeToast");
    if (msg) {
      sessionStorage.removeItem("welcomeToast");
      setWelcomeToast(msg);
      const t = setTimeout(() => setWelcomeToast(null), 4000);
      return () => clearTimeout(t);
    }
  }, [authed]);

  const onAuthed = () => setAuthed(true);

  // A reset/verify link (#reset?token=... or #verify?token=...) must open the
  // Auth screen even if a valid session token already exists in localStorage —
  // otherwise it silently does nothing for already-logged-in users.
  const hasUrlToken = isResetVerifyLink((window.location.hash || "") + (window.location.search || ""));
  if (hasUrlToken) {
    return <Auth initialMode="login" onAuthed={onAuthed} onBack={() => setAuthView(null)} />;
  }

  if (!authed) {
    if (!authView) return <Landing onStart={() => setAuthView("register")} onLogin={() => setAuthView("login")} />;
    return <Auth initialMode={authView} onAuthed={onAuthed} onBack={() => setAuthView(null)} />;
  }
  if (!user) return <div className="empty" style={{ padding: 80 }}>Loading…</div>;
  if (!user.profile_type) return (
    <>
      {welcomeToast && <div className="flash success" role="status">{welcomeToast}</div>}
      <Onboarding onDone={refreshUser} />
    </>
  );

  const doLogout = () => { logout(); setAuthed(false); setUser(null); };
  const [title, subtitle] = TITLES[tab] || ["", ""];
  const ent = user.entitlements || {};
  const nav = user.is_admin ? [...NAV, ADMIN_NAV] : NAV;
  const go = (t) => { setTab(t); setMenuOpen(false); };  // navigate + close mobile drawer
  // Simple multi-card pages flow into a tight masonry. Home/Analytics/Posts/
  // Calendar build their own internal layouts (KPI strips, grids), and form/
  // list-heavy pages stay full-width so inputs aren't cramped.
  const MASONRY_TABS = new Set(["accounts", "leads"]);
  const bodyClass = MASONRY_TABS.has(tab) ? "page-body masonry" : "page-body";

  return (
    <div className={`app ${menuOpen ? "drawer" : ""}`}>
      {welcomeToast && <div className="flash success" role="status">{welcomeToast}</div>}
      <div className="scrim" onClick={() => setMenuOpen(false)} />
      <aside className="sidebar" ref={sidebarRef}>
        <div className="brand">
          <div className="logo">A</div>
          <div>
            <div className="brand-name">Autopilot</div>
            <div className="brand-sub">Your AI marketing team</div>
          </div>
        </div>
        <div style={{ padding: "0 8px 10px", display: "flex", gap: 6 }}>
          <select value={user.active_client_id || "self"} onChange={(e) => switchClient(e.target.value)}
            title="Active client workspace"
            style={{ flex: 1, fontSize: 13, padding: "7px 9px", borderRadius: 9,
                     border: "1px solid var(--line)", background: "#fff", color: "var(--ink)" }}>
            <option value="self">My workspace</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <button onClick={addClient} title="Add client"
            style={{ width: 36, padding: 0, borderRadius: 9, border: "1px solid var(--line)",
                     background: "var(--light)", color: "var(--teal-dark)", cursor: "pointer", fontSize: 16 }}>+</button>
        </div>
        <nav className="nav">
          {nav.map((section) => (
            <div key={section.group}>
              <div className="nav-group">{section.group}</div>
              {section.items.map(([id, label, feat, working]) => {
                // Map feature flags to feature names for permission checks
                const featureMap = {
                  'profile_studio': 'profile_optimizer',
                  'lead_gen': 'lead_gen',
                  'whatsapp_agent': 'whatsapp_agent',
                  'analytics': 'growth_analytics',
                };
                const featureName = featureMap[feat] || feat;

                // Check if feature is hidden (user doesn't have access and it's a gated feature)
                const isHidden = featureName && !hasFeature(user, featureName);
                const locked = feat && ent[feat] === false && !isHidden;

                // If hidden completely, don't render at all
                if (isHidden) {
                  return null;
                }

                return (
                  <button key={id} className={`nav-item ${tab === id ? "active" : ""}`}
                    aria-current={tab === id ? "page" : undefined}
                    title={locked ? "Upgrade your plan to unlock" : working ? "Working 24/7" : undefined}
                    style={locked ? { opacity: 0.5 } : undefined}
                    onClick={() => (locked ? go("accounts") : go(id))}>
                    <span className={`dot ${working && !locked ? "working" : ""}`} /><span>{label}</span>
                    {locked && <span style={{ marginLeft: "auto", fontSize: 10, fontWeight: 700, letterSpacing: "0.05em", color: "var(--teal)" }}>PRO</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          {!user?.is_admin && (
            <button className="nav-item" onClick={() => go("billing")} title="Credits remaining">
              <span className="dot" />
              <span>{user?.subscribed
                ? `${user?.credits ?? 0} credits`
                : `${user?.free_today_remaining ?? 0} free today`}</span>
            </button>
          )}
          <div className="email">{user?.email}</div>
          <button className="nav-item" onClick={doLogout}><span className="dot" /><span>Sign out</span></button>
        </div>
      </aside>

      <main className="main">
        <header className="page-head">
          <button className="menu-btn" ref={menuBtnRef} aria-label="Menu" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}>☰</button>
          <div style={{ flex: 1 }}>
            <h1>{title}</h1>
            <div className="sub">{subtitle}</div>
          </div>
        </header>
        <div className={bodyClass} key={user.active_client_id || "self"}>
          {tab === "home" && (
            <Home
              goTab={setTab}
              user={user}
              onDirective={(text) => { setTeamBrief(text); setTab("team"); }}
            />
          )}
          {tab === "strategy" && <Strategy goTab={setTab} />}
          {tab === "studio" && <Studio />}
          {tab === "videoagent" && <VideoAgent accounts={accounts} />}
          {tab === "whatsappagent" && hasFeature(user, 'whatsapp_agent') && <WhatsAppAgent />}
          {tab === "team" && (
            <ContentTeam
              goTab={setTab}
              initialBrief={teamBrief}
              accounts={accounts}
              goConnect={() => setTab("accounts")}
              onSaved={() => { setPostsRefresh((n) => n + 1); setTab("posts"); }}
            />
          )}
          {tab === "posts" && <Posts refreshKey={postsRefresh} accounts={accounts} />}
          {tab === "campaigns" && <Campaigns accounts={accounts} goTab={setTab} />}
          {tab === "inbox" && <Inbox accounts={accounts} />}
          {tab === "profile" && hasFeature(user, 'profile_optimizer') && <ProfileStudio />}
          {tab === "analytics" && hasFeature(user, 'growth_analytics') && <Analytics />}
          {tab === "accounts" && (
            <Accounts user={user} accounts={accounts} reloadAccounts={reloadAccounts} refreshUser={refreshUser} goTab={setTab} />
          )}
          {tab === "calendar" && <Calendar />}
          {tab === "competitor" && <Competitor />}
          {tab === "listening" && <SocialListening />}
          {tab === "seo" && <SeoGeo />}
          {tab === "opportunities" && <Opportunities goTab={setTab} />}
          {tab === "leads" && hasFeature(user, 'lead_gen') && <Leads refreshUser={refreshUser} />}
          {tab === "connections" && (
            <Connections accounts={accounts} goAccounts={() => setTab("accounts")} goWhatsAppAgent={() => setTab("whatsappagent")} />
          )}
          {tab === "billing" && <Billing user={user} />}
          {tab === "admin" && user.is_admin && <Admin />}
          {tab === "help" && <HelpCenter />}
        </div>
      </main>
    </div>
  );
}
