import { useState } from "react";
import { login, register } from "../api.js";

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
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={submit}>
        <h1>LinkedIn Autopilot</h1>
        <p>{mode === "login" ? "Sign in to your account" : "Create your account"}</p>

        {error && <div className="error">{error}</div>}

        {mode === "register" && (
          <>
            <label>Full name</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Optional" />
          </>
        )}

        <label>Email</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />

        <label>Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          placeholder={mode === "register" ? "At least 8 characters" : ""}
        />

        <div style={{ marginTop: 18 }}>
          <button className="btn-primary" style={{ width: "100%" }} disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </div>

        <div className="auth-toggle">
          {mode === "login" ? (
            <>No account? <a onClick={() => setMode("register")}>Register</a></>
          ) : (
            <>Already have one? <a onClick={() => setMode("login")}>Sign in</a></>
          )}
        </div>
      </form>
    </div>
  );
}
