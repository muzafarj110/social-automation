import { useEffect, useState } from "react";
import { getToken, logout, me, listAccounts } from "./api.js";
import Auth from "./components/Auth.jsx";
import Onboarding from "./components/Onboarding.jsx";
import Wizard from "./components/Wizard.jsx";
import Home from "./components/Home.jsx";
import Strategy from "./components/Strategy.jsx";
import Accounts from "./components/Accounts.jsx";
import Generate from "./components/Generate.jsx";
import Posts from "./components/Posts.jsx";
import Inbox from "./components/Inbox.jsx";
import Campaigns from "./components/Campaigns.jsx";
import Analytics from "./components/Analytics.jsx";
import ProfileStudio from "./components/ProfileStudio.jsx";
import Admin from "./components/Admin.jsx";
import Billing from "./components/Billing.jsx";
import Calendar from "./components/Calendar.jsx";
import Leads from "./components/Leads.jsx";

const NAV = [
  { group: "Overview", items: [["home", "Home", null]] },
  { group: "Create", items: [["campaigns", "Autopilot", "autopilot"], ["generate", "Quick post", "generate"], ["strategy", "Brand voice", "strategy"]] },
  { group: "Manage", items: [["calendar", "Calendar", null], ["posts", "Posts", null], ["inbox", "Inbox", "inbox"]] },
  { group: "Grow", items: [["leads", "Leads", null], ["profile", "Profile", "profile_studio"], ["analytics", "Analytics", "analytics"]] },
  { group: "Settings", items: [["accounts", "Accounts", null], ["billing", "Billing", null]] },
];
// Admin-only nav group, appended when the user is an operator.
const ADMIN_NAV = { group: "Admin", items: [["admin", "Users", null]] };
const TITLES = {
  home: ["Home", "Your week at a glance"],
  strategy: ["Brand voice", "Your voice, persona and positioning — used by every post"],
  generate: ["Quick post", "Write one post right now, by hand with AI"],
  campaigns: ["Autopilot", "Set it once — AI writes, tailors and posts on a schedule"],
  posts: ["Posts", "Drafts, scheduled and published"],
  inbox: ["Inbox", "AI-drafted replies, DMs and outreach to approve"],
  profile: ["Profile Studio", "Optimize your LinkedIn profile"],
  analytics: ["Analytics", "Performance and AI strategy"],
  calendar: ["Calendar", "Everything going out, across every platform"],
  leads: ["Leads", "Capture leads and let AI draft outreach"],
  accounts: ["Accounts", "Keys, connected accounts and usage"],
  billing: ["Billing", "Your credits and top-ups"],
  admin: ["Users", "Manage plans, access and account status"],
};

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()));
  const [user, setUser] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [tab, setTab] = useState("home");
  const [postsRefresh, setPostsRefresh] = useState(0);
  const [wizardSkipped, setWizardSkipped] = useState(
    () => localStorage.getItem("wizard_skipped") === "1"
  );
  const dismissWizard = () => {
    localStorage.setItem("wizard_skipped", "1");
    setWizardSkipped(true);
  };

  const refreshUser = async () => {
    try { setUser(await me()); }
    catch { logout(); setAuthed(false); }
  };
  const reloadAccounts = async () => {
    try { setAccounts(await listAccounts()); } catch { /* ignore */ }
  };

  useEffect(() => {
    if (authed) { refreshUser(); reloadAccounts(); }
  }, [authed]); // eslint-disable-line

  if (!authed) return <Auth onAuthed={() => setAuthed(true)} />;
  if (!user) return <div className="empty" style={{ padding: 80 }}>Loading…</div>;
  if (!user.profile_type) return <Onboarding onDone={refreshUser} />;

  // First-run guided setup: shown until the user connects an account or skips.
  const connected = !!user.has_zernio_key && accounts.length > 0;
  if (!wizardSkipped && !connected) {
    return (
      <Wizard
        user={user}
        accounts={accounts}
        onSkip={dismissWizard}
        goTab={(t) => { dismissWizard(); setTab(t); }}
      />
    );
  }

  const doLogout = () => { logout(); setAuthed(false); setUser(null); };
  const [title, subtitle] = TITLES[tab] || ["", ""];
  const ent = user.entitlements || {};
  const nav = user.is_admin ? [...NAV, ADMIN_NAV] : NAV;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">A</div>
          <div>
            <div className="brand-name">Autopilot</div>
            <div className="brand-sub">AI Marketing</div>
          </div>
        </div>
        <nav className="nav">
          {nav.map((section) => (
            <div key={section.group}>
              <div className="nav-group">{section.group}</div>
              {section.items.map(([id, label, feat]) => {
                const locked = feat && ent[feat] === false;
                return (
                  <button key={id} className={`nav-item ${tab === id ? "active" : ""}`}
                    title={locked ? "Upgrade your plan to unlock" : undefined}
                    style={locked ? { opacity: 0.5 } : undefined}
                    onClick={() => (locked ? setTab("accounts") : setTab(id))}>
                    <span className="dot" /><span>{label}</span>
                    {locked && <span style={{ marginLeft: "auto", fontSize: 10, fontWeight: 700, letterSpacing: "0.05em", color: "#a98bff" }}>PRO</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          {!user?.is_admin && (
            <button className="nav-item" onClick={() => setTab("billing")} title="Credits remaining">
              <span className="dot" /><span>{user?.credits ?? 0} credits</span>
            </button>
          )}
          <div className="email">{user?.email}</div>
          <button className="nav-item" onClick={doLogout}><span className="dot" /><span>Sign out</span></button>
        </div>
      </aside>

      <main className="main">
        <header className="page-head">
          <div>
            <h1>{title}</h1>
            <div className="sub">{subtitle}</div>
          </div>
        </header>
        <div className="page-body">
          {tab === "home" && <Home goTab={setTab} user={user} />}
          {tab === "strategy" && <Strategy />}
          {tab === "generate" && (
            <Generate
              accounts={accounts}
              goConnect={() => setTab("accounts")}
              onSaved={() => { setPostsRefresh((n) => n + 1); setTab("posts"); }}
            />
          )}
          {tab === "posts" && <Posts refreshKey={postsRefresh} />}
          {tab === "campaigns" && <Campaigns accounts={accounts} goTab={setTab} />}
          {tab === "inbox" && <Inbox accounts={accounts} />}
          {tab === "profile" && <ProfileStudio />}
          {tab === "analytics" && <Analytics />}
          {tab === "accounts" && (
            <Accounts user={user} accounts={accounts} reloadAccounts={reloadAccounts} refreshUser={refreshUser} />
          )}
          {tab === "calendar" && <Calendar />}
          {tab === "leads" && <Leads refreshUser={refreshUser} />}
          {tab === "billing" && <Billing user={user} />}
          {tab === "admin" && user.is_admin && <Admin />}
        </div>
      </main>
    </div>
  );
}
