import { useState } from "react";
import LeadGenGuide from "./HelpGuides/LeadGenGuide";
import ContentWorkflowGuide from "./HelpGuides/ContentWorkflowGuide";
import MarketIntelligenceGuide from "./HelpGuides/MarketIntelligenceGuide";
import CampaignsGuide from "./HelpGuides/CampaignsGuide";
import WhatsAppGuide from "./HelpGuides/WhatsAppGuide";
import AgentTeamGuide from "./HelpGuides/AgentTeamGuide";

export default function HelpCenter() {
  const [expanded, setExpanded] = useState(null);

  const toggleSection = (sectionId) => {
    setExpanded(expanded === sectionId ? null : sectionId);
  };

  const guides = [
    { id: "lead-gen", title: "How to generate leads", icon: "🎯", component: LeadGenGuide },
    { id: "content", title: "How to create & distribute content", icon: "📢", component: ContentWorkflowGuide },
    { id: "intel", title: "How to gather market intelligence", icon: "📊", component: MarketIntelligenceGuide },
    { id: "campaigns", title: "How to automate content (Campaigns)", icon: "⚙️", component: CampaignsGuide },
    { id: "whatsapp", title: "How WhatsApp agent works (24/7)", icon: "💬", component: WhatsAppGuide },
    { id: "agents", title: "Understanding your AI agent team", icon: "🤖", component: AgentTeamGuide },
  ];

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto", padding: "0 28px" }}>
      <div style={{ paddingTop: "40px", paddingBottom: "20px", textAlign: "center", borderBottom: "1px solid var(--line)" }}>
        <h1 style={{ fontSize: "32px", margin: "0 0 8px", fontFamily: "Georgia, serif", fontWeight: 400 }}>
          How Autopilot Works
        </h1>
        <p style={{ color: "var(--muted)", fontSize: "14px", margin: 0 }}>
          Learn how to generate leads, create content, and automate your marketing
        </p>
      </div>

      {/* Collapsible Guides */}
      <div style={{ paddingTop: "28px", paddingBottom: "40px" }}>
        {guides.map((guide) => (
          <div key={guide.id} style={{ marginBottom: "12px" }}>
            <button
              onClick={() => toggleSection(guide.id)}
              style={{
                width: "100%",
                padding: "14px 16px",
                background: "var(--card)",
                border: `1px solid ${expanded === guide.id ? "var(--teal)" : "var(--line)"}`,
                borderRadius: "10px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "12px",
                fontSize: "15px",
                fontWeight: 500,
                color: "var(--ink)",
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--light)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "var(--card)";
              }}
            >
              <span style={{ fontSize: "20px" }}>{guide.icon}</span>
              <span style={{ flex: 1, textAlign: "left" }}>{guide.title}</span>
              <span
                style={{
                  fontSize: "18px",
                  transition: "transform 0.2s",
                  transform: expanded === guide.id ? "rotate(180deg)" : "rotate(0deg)",
                }}
              >
                ▼
              </span>
            </button>

            {expanded === guide.id && (
              <div
                style={{
                  background: "var(--light)",
                  border: "1px solid var(--line)",
                  borderTop: "none",
                  borderRadius: "0 0 10px 10px",
                  padding: "20px 16px",
                  animation: "slideDown 0.2s ease-out",
                }}
              >
                <guide.component />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* FAQ Section */}
      <div style={{ marginBottom: "40px", paddingBottom: "28px", borderTop: "1px solid var(--line)", paddingTop: "28px" }}>
        <h2 style={{ fontSize: "18px", fontFamily: "Georgia, serif", fontWeight: 400, margin: "0 0 16px" }}>
          Quick Answers
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "14px" }}>
          <FAQItem question="What's a credit?" answer="1 credit = 1 text/caption post. 2 credits = long-form post. 5 = image post. 15 = video. Check Billing tab to see current costs." />
          <FAQItem question="How do I connect LinkedIn?" answer="Go to Settings → Accounts → Connect LinkedIn → sign in via OAuth. You can connect multiple accounts." />
          <FAQItem question="Can my team use this?" answer="Yes! Feature coming soon: invite team members and set permissions (coming in 2 weeks)." />
          <FAQItem question="Do I need to code?" answer="No coding needed. Everything works through the UI. Just click and fill in forms." />
          <FAQItem question="Can I publish to TikTok/Instagram?" answer="Yes! Autopilot publishes to 15+ platforms: LinkedIn, Twitter, Instagram, TikTok, Facebook, Pinterest, Reddit, YouTube, Bluesky, Threads, Snapchat, Discord, Telegram, WhatsApp, and more." />
          <FAQItem question="What if I run out of credits?" answer="You can buy more in the Billing tab (one-time packs) or upgrade to a monthly plan. Free trial gives you 5 credits/day for 14 days." />
        </div>
      </div>

      <style>{`
        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}

function FAQItem({ question, answer }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        background: "var(--card)",
        border: "1px solid var(--line)",
        borderRadius: "10px",
        padding: "14px",
        cursor: "pointer",
      }}
      onClick={() => setExpanded(!expanded)}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: "8px" }}>
        <span style={{ color: "var(--teal)", fontWeight: 600, marginTop: "2px" }}>Q:</span>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: "13px", fontWeight: 500, margin: "0 0 4px", color: "var(--ink)" }}>{question}</p>
          {expanded && (
            <p style={{ fontSize: "12px", color: "var(--muted)", lineHeight: "1.6", margin: "6px 0 0" }}>
              {answer}
            </p>
          )}
        </div>
        <span style={{ fontSize: "12px", color: "var(--muted)" }}>{expanded ? "−" : "+"}</span>
      </div>
    </div>
  );
}
