import { useEffect, useState } from "react";
import { getToken, logout, me, listAccounts } from "./api.js";
import Auth from "./components/Auth.jsx";
import Home from "./components/Home.jsx";
import Strategy from "./components/Strategy.jsx";
import Accounts from "./components/Accounts.jsx";
import Generate from "./components/Generate.jsx";
import Posts from "./components/Posts.jsx";
import Inbox from "./components/Inbox.jsx";
import Campaigns from "./components/Campaigns.jsx";
import Analytics from "./components/Analytics.jsx";
import ProfileStudio from "./components/ProfileStudio.jsx";

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()));
  const [user, setUser] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [tab, setTab] = useState("home");
  const [postsRefresh, setPostsRefresh] = useState(0);

  const refreshUser = async () => {
    try {
      setUser(await me());
    } catch {
      // token invalid/expired
      logout();
      setAuthed(false);
    }
  };

  const reloadAccounts = async () => {
    try {
      setAccounts(await listAccounts());
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    if (authed) {
      refreshUser();
      reloadAccounts();
    }
  }, [authed]); // eslint-disable-line

  if (!authed) return <Auth onAuthed={() => setAuthed(true)} />;

  const doLogout = () => {
    logout();
    setAuthed(false);
    setUser(null);
  };

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>LinkedIn Autopilot</h1>
          <div className="sub">{user?.email}</div>
        </div>
        <button className="btn-secondary" onClick={doLogout}>
          Sign out
        </button>
      </div>

      <div className="container">
        <div className="tabs">
          {[
            ["home", "Home"],
            ["strategy", "Strategy"],
            ["generate", "Generate"],
            ["campaigns", "Autopilot"],
            ["posts", "Posts"],
            ["inbox", "Inbox"],
            ["profile", "Profile"],
            ["analytics", "Analytics"],
            ["accounts", "Accounts"],
          ].map(([id, label]) => (
            <div
              key={id}
              className={`tab ${tab === id ? "active" : ""}`}
              onClick={() => setTab(id)}
            >
              {label}
            </div>
          ))}
        </div>

        {tab === "home" && <Home goTab={setTab} />}
        {tab === "strategy" && <Strategy />}
        {tab === "generate" && (
          <Generate
            accounts={accounts}
            goConnect={() => setTab("accounts")}
            onSaved={() => {
              setPostsRefresh((n) => n + 1);
              setTab("posts");
            }}
          />
        )}
        {tab === "posts" && <Posts refreshKey={postsRefresh} />}
        {tab === "campaigns" && <Campaigns accounts={accounts} />}
        {tab === "inbox" && <Inbox accounts={accounts} />}
        {tab === "profile" && <ProfileStudio />}
        {tab === "analytics" && <Analytics />}
        {tab === "accounts" && (
          <Accounts
            user={user}
            accounts={accounts}
            reloadAccounts={reloadAccounts}
            refreshUser={refreshUser}
          />
        )}
      </div>
    </div>
  );
}
