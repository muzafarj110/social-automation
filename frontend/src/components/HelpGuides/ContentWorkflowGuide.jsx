export default function ContentWorkflowGuide() {
  const steps = [
    {
      num: 1,
      title: "Define your brand voice (Brand Strategist)",
      description: "Go to Brand strategist → answer questions about your voice, audience, positioning, UVP. Save it. Every AI agent reads this.",
      why: "Without this, each post sounds different. With it, all 6 agents write in your voice automatically.",
    },
    {
      num: 2,
      title: "Connect your social accounts (Accounts)",
      description:
        "Go to Settings → Accounts → Connect LinkedIn, Twitter, Instagram, TikTok, Facebook, etc. Click each platform, sign in via OAuth.",
      why: "Autopilot can't publish if accounts aren't connected. Connect only the platforms you actually use.",
    },
    {
      num: 3,
      title: "Create content (Content Agent)",
      description:
        'Go to Content agent → choose "Just one post now" OR "Plan a week". Write a brief (topic, audience, tone). AI drafts full posts + hashtags.',
      why: "AI writes faster than you. Posts are tailored to your brand voice. You review for 10 seconds, not 30 minutes.",
    },
    {
      num: 4,
      title: "Review & approve (Inbox)",
      description:
        "Go to Inbox → see all pending drafts → click each one → edit if needed → click Approve. All approved posts will publish.",
      why: "One final quality check before anything goes live. Rejects get re-drafted by AI.",
    },
    {
      num: 5,
      title: "Publish to all platforms (Auto)",
      description:
        "Click Schedule → pick a time → choose which platforms to publish to. Autopilot auto-formats each post for each platform.",
      why:
        "One LinkedIn post becomes: a threaded tweet, an Instagram caption, a TikTok description, etc. All at once. Multi-channel without the work.",
    },
  ];

  return (
    <div>
      <p style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "16px", lineHeight: "1.6" }}>
        Creating content is a 5-step workflow. Each step is handled by a different tool. Here's how they work together:
      </p>

      {steps.map((step) => (
        <div key={step.num} style={{ marginBottom: "14px" }}>
          <div
            style={{
              display: "flex",
              gap: "14px",
              alignItems: "flex-start",
              background: "var(--card)",
              border: "1px solid var(--line)",
              borderRadius: "8px",
              padding: "14px",
            }}
          >
            <div
              style={{
                minWidth: "32px",
                height: "32px",
                borderRadius: "50%",
                background: "var(--teal)",
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "14px",
                fontWeight: 600,
                flexShrink: 0,
              }}
            >
              {step.num}
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--ink)", margin: "0 0 6px" }}>
                {step.title}
              </p>
              <p style={{ fontSize: "12px", color: "var(--muted)", lineHeight: "1.5", margin: "0 0 6px" }}>
                {step.description}
              </p>
              <p style={{ fontSize: "11px", color: "var(--teal-deep)", fontWeight: 500, margin: 0 }}>
                💡 Why: {step.why}
              </p>
            </div>
          </div>
        </div>
      ))}

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
          <strong>⏱️ Time to first post:</strong> ~15 minutes. Define brand voice (5 min) → Connect account (3 min) → Draft post (2 min) → Approve (1 min) → Publish (1 min). Everything is live.
        </p>
      </div>
    </div>
  );
}
