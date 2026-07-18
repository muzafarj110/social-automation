export default function AgentTeamGuide() {
  const agents = [
    {
      name: "Content Agent",
      role: "Writer",
      what: "Drafts individual posts or plans a week of content",
      use: "Go to Content Agent → write a brief → AI drafts full posts with hashtags",
    },
    {
      name: "Brand Strategist",
      role: "Voice Keeper",
      what: "Defines your brand voice, positioning, UVP",
      use: "Set it once → every other agent reads it → all content stays on-brand",
    },
    {
      name: "Campaigns",
      role: "Scheduler",
      what: "Auto-generates posts on a repeating schedule",
      use: "Set topics → AI generates fresh posts every 15 min → publish on your schedule",
    },
    {
      name: "Competitor Agent",
      role: "Market Scout",
      what: "Monitors rivals, surfaces winning tactics",
      use: "Add competitor by name → AI analyzes posts → shows gaps you can exploit",
    },
    {
      name: "Social Listening",
      role: "Ear on Market",
      what: "Finds high-intent people discussing your space",
      use: "Track a keyword → AI finds prospects + patterns",
    },
    {
      name: "SEO + GEO Agent",
      role: "Opportunity Finder",
      what: "Finds keyword gaps, visibility opportunities",
      use: "Enter keywords → AI returns gaps + AI citation strategies + SEO fixes",
    },
    {
      name: "Lead-Gen Agent",
      role: "Sales Helper",
      what: "Drafts personalized outreach messages",
      use: "Add prospect → click Draft outreach → AI writes personalized message",
    },
    {
      name: "Opportunities",
      role: "Task Master",
      what: "Smart to-do list of what needs attention",
      use: "Shows: setup tasks, pending approvals, leads without outreach, posts due",
    },
    {
      name: "Growth Analytics",
      role: "Performance Coach",
      what: "Shows LinkedIn performance + AI insights",
      use: "Link LinkedIn → AI pulls metrics → tells you what's working",
    },
    {
      name: "Profile Optimizer",
      role: "Profile Editor",
      what: "Generates LinkedIn/Twitter profile copy",
      use: "Tell it your info → AI drafts headline, About section, recommendations",
    },
    {
      name: "Studio",
      role: "Toolbox",
      what: "24 one-off tools for ad-hoc content",
      use: "Email sequences, graphics, reports, SEO audits, etc. on demand",
    },
    {
      name: "Video Agent",
      role: "Videographer",
      what: "Turns topics into short + long videos",
      use: "Set up channel → enter topic → AI generates script, footage, voiceover, videos",
    },
    {
      name: "WhatsApp Agent",
      role: "Customer Service 24/7",
      what: "Answers customer questions automatically",
      use: "Setup FAQ → customers message → AI replies instantly, 24/7",
    },
  ];

  return (
    <div>
      <p style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "16px", lineHeight: "1.6" }}>
        Autopilot isn't one tool — it's a team of 13 AI agents, each with a specific job. They work together: Content Agent drafts → Brand Strategist ensures brand voice → Campaigns automates → Analytics measures impact. Here's what each does:
      </p>

      <div style={{ display: "grid", gap: "10px" }}>
        {agents.map((agent, idx) => (
          <div
            key={idx}
            style={{
              background: "var(--card)",
              border: "1px solid var(--line)",
              borderRadius: "8px",
              padding: "12px 14px",
              display: "grid",
              gridTemplateColumns: "auto 1fr",
              gap: "12px",
              alignItems: "start",
            }}
          >
            <div
              style={{
                minWidth: "32px",
                height: "32px",
                borderRadius: "50%",
                background: "var(--teal-tint)",
                border: "1px solid var(--teal)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "11px",
                fontWeight: 600,
                color: "var(--teal-deep)",
                flexShrink: 0,
              }}
            >
              {idx + 1}
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginBottom: "4px" }}>
                <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--ink)", margin: 0 }}>
                  {agent.name}
                </p>
                <span
                  style={{
                    fontSize: "11px",
                    color: "var(--teal)",
                    background: "var(--teal-tint)",
                    padding: "2px 8px",
                    borderRadius: "4px",
                    fontWeight: 500,
                  }}
                >
                  {agent.role}
                </span>
              </div>
              <p style={{ fontSize: "12px", color: "var(--muted)", margin: "0 0 4px", lineHeight: "1.4" }}>
                {agent.what}
              </p>
              <p style={{ fontSize: "11px", color: "var(--teal-deep)", margin: 0 }}>
                <strong>→ How to use:</strong> {agent.use}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: "16px",
          padding: "12px 14px",
          background: "var(--teal-tint)",
          border: "1px solid var(--teal)",
          borderRadius: "8px",
        }}
      >
        <p style={{ fontSize: "12px", color: "var(--teal-deep)", margin: "0 0 6px", fontWeight: 500 }}>
          🤖 How They Work Together:
        </p>
        <p style={{ fontSize: "11px", color: "var(--teal-deep)", lineHeight: "1.6", margin: 0 }}>
          <strong>Example Day:</strong> You write a brief → Content Agent drafts posts + Campaigns auto-generates more posts → All read Brand Strategist to stay on-voice → Posts publish to all platforms → Competitor Agent finds a rival's winning tactic → you write about it → Lead-Gen Agent drafts outreach to prospects → Analytics shows your post got 200 impressions → WhatsApp Agent answers customer questions 24/7. All 13 agents working in parallel. You just created a brief.
        </p>
      </div>
    </div>
  );
}
