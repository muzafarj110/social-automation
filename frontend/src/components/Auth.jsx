import { useState } from "react";
import { login, register } from "../api.js";

const POINTS = [
  "Generate on-brand content with AI, quality-checked before it posts",
  "Put posting on autopilot — schedule weeks ahead, hands-free",
  "Optimize your profile and learn from what actually performs",
];

export default function Auth({ onAuthed }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, fullName || null);
      onAuthed();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <div className="auth-brand">
        <div className="logo">A</div>
        <h1>Your AI marketing department, on autopilot.</h1>
        <p>
          Autopilot builds your brand, writes and schedules your content, handles
          engagement, and learns from results — so your marketing runs itself.
        </p>
        <div className="auth-points">
          {POINTS.map((p) => (
            <div className="auth-point" key={p}><span className="tick">✓</span><span>{p}</span></div>
          ))}
        </div>
        <div className="auth-trust">Built on the AI Models Hub · Your data stays yours · Ban-safe automation</div>
      </div>

      <div className="auth-form-wrap">
        <form className="auth-card" onSubmit={submit}>
          <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
          <div className="lead">
            {mode === "login" ? "Sign in to your workspace." : "Start automating your marketing in minutes."}
          </div>

          {error && <div className="error">{error}</div>}

          {mode === "register" && (
            <>
              <label>Full name</label>
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Optional" />
            </>
          )}

          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="you@company.com" />

          <label>Password</label>
          <input
            type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            required minLength={8}
            placeholder={mode === "register" ? "At least 8 characters" : "••••••••"}
          />

          <div style={{ marginTop: 18 }}>
            <button className="btn-primary" style={{ width: "100%" }} disabled={busy}>
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </div>

          <div className="auth-toggle">
            {mode === "login" ? (
              <>New here? <a onClick={() => setMode("register")}>Create an account</a></>
            ) : (
              <>Already have an account? <a onClick={() => setMode("login")}>Sign in</a></>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
