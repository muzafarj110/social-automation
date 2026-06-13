import { useState } from "react";
import { setProfile } from "../api.js";

const PROFILES = [
  { id: "individual", label: "Individual", desc: "Grow my own professional presence — mostly hands-off." },
  { id: "influencer", label: "Influencer / Creator", desc: "High-volume, multi-format content and engagement." },
  { id: "startup", label: "Startup", desc: "Build the brand and generate leads." },
  { id: "company", label: "Company / Agency", desc: "A team managing one or more brands." },
];

export default function Onboarding({ onDone }) {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const pick = async (id) => {
    setBusy(id); setError("");
    try { await setProfile(id); onDone(); }
    catch (e) { setError(e.message); setBusy(""); }
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", display: "grid", placeItems: "center", padding: 24 }}>
      <div style={{ width: "100%", maxWidth: 720 }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div className="logo" style={{
            width: 46, height: 46, borderRadius: 13, margin: "0 auto 14px",
            background: "linear-gradient(135deg, var(--teal), #a98bff)",
            display: "grid", placeItems: "center", fontWeight: 800, fontSize: 24, color: "#1a0f3a",
          }}>A</div>
          <h1 style={{ fontSize: 26 }}>Welcome — who are we building for?</h1>
          <p className="muted" style={{ marginTop: 6 }}>
            We'll tailor your workspace and recommendations. You can change this later.
          </p>
        </div>

        {error && <div className="error">{error}</div>}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14 }}>
          {PROFILES.map((p) => (
            <button key={p.id} onClick={() => pick(p.id)} disabled={!!busy}
              style={{
                textAlign: "left", background: "#fff", border: "1px solid var(--line)",
                borderRadius: "var(--radius-lg)", padding: "18px 20px", cursor: "pointer",
              }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: "var(--ink)", marginBottom: 6 }}>
                {busy === p.id ? "Setting up…" : p.label}
              </div>
              <div className="muted" style={{ fontSize: 13 }}>{p.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
