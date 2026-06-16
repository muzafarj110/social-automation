import { useEffect, useState } from "react";
import { listCampaigns, getBrand } from "../api.js";

// Profile-tailored welcome line.
const LEAD = {
  individual: "Let's get you posting consistently — mostly hands-off.",
  influencer: "Let's build your content engine across platforms.",
  startup: "Let's turn your brand into a lead machine.",
  company: "Let's set up your brand's marketing workspace.",
};

// A focused, one-screen guided setup shown to new users before the full app.
// Each step has a single clear action; users can skip to the dashboard anytime.
export default function Wizard({ user, accounts = [], goTab, onSkip }) {
  const [campaigns, setCampaigns] = useState(null);
  const [brand, setBrand] = useState(null);

  useEffect(() => {
    listCampaigns().then(setCampaigns).catch(() => setCampaigns([]));
    getBrand().then(setBrand).catch(() => setBrand({}));
  }, []);

  const connected = accounts.length > 0;
  const brandReady = !!(brand && (brand.voice || brand.brand_name));
  const hasCampaign = (campaigns?.length || 0) > 0;

  const steps = [
    { done: true, title: "Tell us who you are",
      desc: `You're set up as a ${user?.profile_type || "creator"}. Your workspace is tailored to that.` },
    { done: connected, title: "Connect a social account", tab: "accounts", cta: "Connect account",
      desc: "Connect your channels and link an account on any of 15 platforms — this is how Autopilot posts for you." },
    { done: brandReady, optional: true, title: "Set your brand voice", tab: "strategy", cta: "Set brand voice",
      desc: "Optional: tell the AI your voice and audience so every post sounds like you." },
    { done: hasCampaign, title: "Launch your first campaign", tab: "campaigns", cta: "Create campaign",
      desc: "Pick platforms and topics — the AI writes, tailors per platform, quality-checks and schedules." },
  ];

  // The next thing to do = first required step that's not done (fall back to first optional).
  const currentIdx = steps.findIndex((s) => !s.done && !s.optional);
  const activeIdx = currentIdx === -1 ? steps.findIndex((s) => !s.done) : currentIdx;
  const doneCount = steps.filter((s) => s.done).length;
  const lead = LEAD[user?.profile_type] || "A few quick steps to put your marketing on autopilot.";

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg, #f7f7fb)", display: "grid", placeItems: "center", padding: "40px 16px" }}>
      <div style={{ width: "100%", maxWidth: 620 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 18 }}>
          <div className="logo" style={{ width: 40, height: 40, borderRadius: 10, background: "var(--teal)", color: "#fff", display: "grid", placeItems: "center", fontWeight: 800 }}>A</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 20, color: "#1f2333" }}>Welcome to Autopilot</div>
            <div className="muted" style={{ fontSize: 13 }}>{lead}</div>
          </div>
        </div>

        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          {steps.map((s, i) => {
            const isActive = i === activeIdx;
            return (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 14, padding: "16px 18px",
                borderTop: i ? "1px solid #ececf3" : "none",
                background: isActive ? "#faf9ff" : "transparent",
              }}>
                <span style={{
                  width: 28, height: 28, borderRadius: "50%", display: "grid", placeItems: "center",
                  fontSize: 14, fontWeight: 700, flexShrink: 0,
                  background: s.done ? "#dcfce7" : isActive ? "var(--teal)" : "#eceaf6",
                  color: s.done ? "#166534" : isActive ? "#fff" : "#8b8fa3",
                }}>{s.done ? "✓" : i + 1}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: "#1f2333" }}>
                    {s.title}{s.optional && !s.done ? <span className="muted" style={{ fontWeight: 400 }}> · optional</span> : ""}
                  </div>
                  <div className="muted" style={{ fontSize: 13 }}>{s.desc}</div>
                </div>
                {s.done ? (
                  <span className="badge published">Done</span>
                ) : isActive && s.tab ? (
                  <button className="btn-primary" onClick={() => goTab(s.tab)}>{s.cta}</button>
                ) : s.tab ? (
                  <button className="btn-secondary" onClick={() => goTab(s.tab)} style={{ opacity: 0.7 }}>{s.cta}</button>
                ) : null}
              </div>
            );
          })}
        </div>

        <div style={{ display: "flex", alignItems: "center", marginTop: 16 }}>
          <span className="muted" style={{ fontSize: 13 }}>{doneCount} of {steps.length} done</span>
          <div style={{ flex: 1 }} />
          <button className="btn-ghost" onClick={onSkip}>Skip setup — explore the app →</button>
        </div>
      </div>
    </div>
  );
}
