import { useState } from "react";

export default function LeadGenGuide() {
  const [activeMethod, setActiveMethod] = useState(1);

  const Method = ({ num, title, steps }) => (
    <div
      onClick={() => setActiveMethod(activeMethod === num ? null : num)}
      style={{
        marginBottom: "14px",
        cursor: "pointer",
      }}
    >
      <div
        style={{
          background: activeMethod === num ? "var(--teal-tint)" : "var(--card)",
          border: activeMethod === num ? "1px solid var(--teal)" : "1px solid var(--line)",
          borderRadius: "8px",
          padding: "12px 14px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
          transition: "all 0.2s",
        }}
      >
        <span style={{ fontSize: "16px", fontWeight: 600, color: "var(--teal-deep)" }}>Method {num}:</span>
        <span style={{ flex: 1, fontSize: "14px", fontWeight: 500, color: "var(--ink)" }}>{title}</span>
        <span style={{ fontSize: "12px", color: "var(--muted)" }}>{activeMethod === num ? "−" : "+"}</span>
      </div>

      {activeMethod === num && (
        <div style={{ marginTop: "10px", paddingLeft: "12px", borderLeft: "2px solid var(--teal)" }}>
          {steps.map((step, idx) => (
            <div key={idx} style={{ marginBottom: "12px" }}>
              <div
                style={{
                  display: "flex",
                  gap: "12px",
                  alignItems: "flex-start",
                  background: "var(--card)",
                  border: "1px solid var(--line)",
                  borderRadius: "8px",
                  padding: "12px 14px",
                }}
              >
                <div
                  style={{
                    minWidth: "28px",
                    height: "28px",
                    borderRadius: "50%",
                    background: "var(--teal)",
                    color: "#fff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "12px",
                    fontWeight: 600,
                    flexShrink: 0,
                  }}
                >
                  {idx + 1}
                </div>
                <div>
                  <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--ink)", margin: "0 0 4px" }}>
                    {step.title}
                  </p>
                  <p style={{ fontSize: "12px", color: "var(--muted)", lineHeight: "1.5", margin: 0 }}>
                    {step.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div>
      <p style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "16px", lineHeight: "1.6" }}>
        There are 3 ways to generate leads with Autopilot. Each works differently — choose based on your sales motion.
      </p>

      <Method
        num={1}
        title="LinkedIn Outreach (Manual, 1-to-1)"
        steps={[
          {
            title: "Add a prospect",
            description:
              'Go to Leads tab → click "Add prospect" → enter name, title, company. Optional: paste their LinkedIn profile URL.',
          },
          {
            title: "AI drafts personalized message",
            description:
              "Click 'Draft outreach'. AI reads their info + your brand voice + your positioning, and writes a custom message in seconds. Not spammy, personalized.",
          },
          {
            title: "Review & send on LinkedIn",
            description:
              "Copy the draft message → paste it into LinkedIn DM (or email). We can't auto-send via LinkedIn API, so you send manually. They reply → conversation starts.",
          },
        ]}
      />

      <Method
        num={2}
        title="WhatsApp Agent (Automated 24/7)"
        steps={[
          {
            title: "Setup once (15-30 min)",
            description:
              "Go to WhatsApp agent → follow 6-step wizard → create Meta Developer App → connect WhatsApp Business number → build FAQ knowledge base.",
          },
          {
            title: "Customer messages you",
            description:
              'Customer sends a WhatsApp message: "Hi, do you have a free trial?" No waiting for you to see it.',
          },
          {
            title: "AI replies instantly (24/7)",
            description:
              "AI reads your FAQ, replies instantly: 'Yes! Free trial includes 50 credits...' All automatic. No human review needed. Sensitive topics (refunds, complaints) get flagged for you to see.",
          },
          {
            title: "Qualified conversations",
            description:
              "Customers get instant answers → they're more engaged → when they message you back, it's a real conversation, not a cold call.",
          },
        ]}
      />

      <Method
        num={3}
        title="Content → Inbound (Passive, Long-term)"
        steps={[
          {
            title: "Create great content",
            description:
              "Use Content agent or Campaigns to post consistently to all platforms (LinkedIn, Twitter, Instagram, etc.).",
          },
          {
            title: "Stay visible",
            description:
              "Posts get seen by your market → people recognize your brand → builds trust over time.",
          },
          {
            title: "People message you",
            description:
              "Prospects message you on LinkedIn, Twitter, or WhatsApp → inbound leads. They're already interested because they know who you are.",
          },
          {
            title: "Same AI outreach",
            description:
              "Use Lead-gen agent to draft replies. Or use WhatsApp agent to auto-reply 24/7. Either way, your AI handles the initial response.",
          },
        ]}
      />

      <div
        style={{
          marginTop: "16px",
          padding: "12px 14px",
          background: "var(--teal-tint)",
          border: "1px solid var(--teal)",
          borderRadius: "8px",
        }}
      >
        <p style={{ fontSize: "12px", color: "var(--teal-deep)", margin: 0, lineHeight: "1.5" }}>
          <strong>💡 Pro tip:</strong> Use all 3 at once. Content keeps you visible → WhatsApp agent converts inbound → manual outreach to warm prospects you find. Mix and match.
        </p>
      </div>
    </div>
  );
}
