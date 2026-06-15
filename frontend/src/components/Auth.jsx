import { useEffect, useState } from "react";
import { login, register, forgotPassword, resetPassword, verifyEmail, resendVerification } from "../api.js";

const POINTS = [
  "Generate on-brand content with AI, quality-checked before it posts",
  "Put posting on autopilot — schedule weeks ahead, hands-free",
  "Optimize your profile and learn from what actually performs",
];

// Pull a token out of the URL for a given flow (#reset?token=… / #verify?token=…).
function readToken(kind) {
  if (typeof window === "undefined") return "";
  const h = window.location.hash || "";
  const s = window.location.search || "";
  const m = (h + s).match(/[?&]token=([^&]+)/);
  return m && new RegExp(kind, "i").test(h + s) ? decodeURIComponent(m[1]) : "";
}

export default function Auth({ onAuthed }) {
  const [mode, setMode] = useState("login"); // login | register | forgot | reset | verify
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [needsVerify, setNeedsVerify] = useState(false);

  useEffect(() => {
    const r = readToken("reset");
    if (r) { setResetToken(r); setMode("reset"); return; }
    const v = readToken("verify");
    if (v) {
      setMode("verify"); setBusy(true);
      verifyEmail(v)
        .then(() => { window.history.replaceState({}, "", window.location.pathname); onAuthed(); })
        .catch((e) => { setError(e.message || "Verification failed."); setBusy(false); });
    }
  }, []); // eslint-disable-line

  const doResend = async () => {
    setError(""); setBusy(true);
    try {
      const r = await resendVerification(email);
      setInfo(r?.message || "If that account needs verifying, a new link is on its way.");
      setNeedsVerify(false);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setInfo(""); setNeedsVerify(false); setBusy(true);
    try {
      if (mode === "login") { await login(email, password); onAuthed(); }
      else if (mode === "register") {
        const r = await register(email, password, fullName || null);
        if (r.verification_required) {
          setInfo(r.message || "Account created. Check your email to verify, then sign in.");
          setMode("login"); setPassword("");
        } else { onAuthed(); }
      }
      else if (mode === "forgot") {
        const r = await forgotPassword(email);
        setInfo(r?.message || "If that email is registered, a reset link is on its way.");
      } else if (mode === "reset") {
        await resetPassword(resetToken, password);
        window.history.replaceState({}, "", window.location.pathname);
        onAuthed();
      }
    } catch (err) {
      setError(err.message);
      if (err.status === 403) setNeedsVerify(true);  // unverified email on login
    } finally {
      setBusy(false);
    }
  };

  const titles = {
    login: "Welcome back", register: "Create your account",
    forgot: "Reset your password", reset: "Choose a new password",
    verify: "Verifying your email",
  };
  const leads = {
    login: "Sign in to your workspace.",
    register: "Start automating your marketing in minutes.",
    forgot: "Enter your email and we'll send you a reset link.",
    reset: "Enter a new password for your account.",
    verify: "Hang tight while we confirm your address.",
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
        <div className="auth-trust">Powered by AI · Your data stays yours · Ban-safe automation</div>
      </div>

      <div className="auth-form-wrap">
        <form className="auth-card" onSubmit={submit}>
          <h2>{titles[mode]}</h2>
          <div className="lead">{leads[mode]}</div>

          {error && <div className="error">{error}</div>}
          {info && <div className="success">{info}</div>}

          {mode === "verify" ? (
            <div style={{ marginTop: 10 }}>
              {busy
                ? <div className="empty"><span className="spinner" />Verifying…</div>
                : <a onClick={() => { setMode("login"); setError(""); }}>← Back to sign in</a>}
            </div>
          ) : (
            <>
              {mode === "register" && (
                <>
                  <label>Full name</label>
                  <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Optional" />
                </>
              )}

              {(mode === "login" || mode === "register" || mode === "forgot") && (
                <>
                  <label>Email</label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="you@company.com" />
                </>
              )}

              {(mode === "login" || mode === "register" || mode === "reset") && (
                <>
                  <label>{mode === "reset" ? "New password" : "Password"}</label>
                  <input
                    type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                    required minLength={8}
                    placeholder={mode === "login" ? "••••••••" : "At least 8 characters"}
                  />
                </>
              )}

              <div style={{ marginTop: 18 }}>
                <button className="btn-primary" style={{ width: "100%" }} disabled={busy}>
                  {busy ? "Please wait…"
                    : mode === "login" ? "Sign in"
                    : mode === "register" ? "Create account"
                    : mode === "forgot" ? "Send reset link"
                    : "Set new password"}
                </button>
              </div>

              {needsVerify && (
                <div className="auth-toggle" style={{ marginTop: 10 }}>
                  Didn't get the email? <a onClick={doResend}>Resend verification link</a>
                </div>
              )}
              {mode === "login" && (
                <div className="auth-toggle" style={{ marginTop: 10 }}>
                  <a onClick={() => { setMode("forgot"); setError(""); setInfo(""); }}>Forgot password?</a>
                </div>
              )}

              <div className="auth-toggle">
                {mode === "login" && <>New here? <a onClick={() => { setMode("register"); setError(""); setInfo(""); }}>Create an account</a></>}
                {mode === "register" && <>Already have an account? <a onClick={() => { setMode("login"); setError(""); setInfo(""); }}>Sign in</a></>}
                {(mode === "forgot" || mode === "reset") && <a onClick={() => { setMode("login"); setError(""); setInfo(""); }}>← Back to sign in</a>}
              </div>
            </>
          )}
        </form>
      </div>
    </div>
  );
}
