import { useEffect, useState } from "react";
import { getToken, logout, me, listAccounts } from "./api.js";
import Auth from "./components/Auth.jsx";
import Onboarding from "./components/Onboarding.jsx";
import Home from "./components/Home.jsx";
import Strategy from "./components/Strategy.jsx";
import Accounts from "./components/Accounts.jsx";
import Generate from "./components/Generate.jsx";
import Posts from "./components/Posts.jsx";
import Inbox from "./components/Inbox.jsx";
import Campaigns from "./components/Campaigns.jsx";
import Analytics from "./components/Analytics.jsx";
import ProfileStudio from "./components/ProfileStudio.jsx";

const NAV = [
  { group: "Overview", items: [["home", "Home", null]] },
  { group: "Create", items: [["strategy", "Strategy", "strategy"], ["generate", "Generate", "generate"], ["campaigns", "Autopilot", "autopilot"]] },
  { group: "Manage", items: [["posts", "Posts", null], ["inbox", "Inbox", "inbox"]] },
  { group: "Grow", items: [["profile", "Profile", "profile_studio"], ["analytics", "Analytics", "analytics"]] },
  { group: "Settings", items: [["accounts", "Accounts", null]] },
];
const TITLES = {
  home: ["Home", "Your week at a glance"],
  strategy: ["Strategy", "Your brand voice, persona and positioning"],
  generate: ["Generate", "Create a single post with AI"],
  campaigns: ["Autopilot", "Hands-off campaigns that post for you"],
  posts: ["Posts", "Drafts, scheduled and published"],
  inbox: ["Inbox", "AI-drafted replies, DMs and outreach to approve"],
  profile: ["Profile Studio", "Optimize your LinkedIn profile"],
  analytics: ["Analytics", "Performance and AI strategy"],
  accounts: ["Accounts", "Keys, connected accounts and usage"],
};

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()));
  const [user, setUser] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [tab, setTab] = useState("home");
  const [postsRefresh, setPostsRefresh] = useState(0);

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

  const doLogout = () => { logout(); setAuthed(false); setUser(null); };
  const [title, subtitle] = TITLES[tab] || ["", ""];
  const ent = user.entitlements || {};

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
          {NAV.map((section) => (
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
          {tab === "home" && <Home goTab={setTab} />}
          {tab === "strategy" && <Strategy />}
          {tab === "generate" && (
            <Generate
              accounts={accounts}
              goConnect={() => setTab("accounts")}
              onSaved={() => { setPostsRefresh((n) => n + 1); setTab("posts"); }}
            />
          )}
          {tab === "posts" && <Posts refreshKey={postsRefresh} />}
          {tab === "campaigns" && <Campaigns accounts={accounts} />}
          {tab === "inbox" && <Inbox accounts={accounts} />}
          {tab === "profile" && <ProfileStudio />}
          {tab === "analytics" && <Analytics />}
          {tab === "accounts" && (
            <Accounts user={user} accounts={accounts} reloadAccounts={reloadAccounts} refreshUser={refreshUser} />
          )}
        </div>
      </main>
    </div>
  );
}
