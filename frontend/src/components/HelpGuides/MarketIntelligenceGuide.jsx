export default function MarketIntelligenceGuide() {
  const agents = [
    {
      name: "Competitor Agent",
      emoji: "🔍",
      what: "Monitors your rivals",
      how: "Add a competitor by name/website → AI analyzes their posts → surfaces winning tactics → shows gaps you can exploit",
      example: "Sees competitor posting about 'ROI stories' getting 10x engagement → you write similar content",
    },
    {
      name: "Social Listening",
      emoji: "👂",
      what: "Finds people actively discussing your market",
      how: "Enter a keyword (e.g., 'AI tools for startups') → AI scans across platforms → surfaces patterns and high-intent prospects",
      example: "Finds 50 CTOs discussing 'migration from legacy systems' → you write about smooth migration stories",
    },
    {
      name: "SEO + GEO Agent",
      emoji: "🔎",
      what: "Finds keywords & visibility opportunities",
      how: "Enter your website + target keywords → AI returns long-tail keyword gaps, how to get cited in ChatGPT, technical SEO fixes",
      example: "Discovers 'AI for financial services' has low competition → you publish about this → ranks fast",
    },
    {
      name: "Opportunities",
      emoji: "📌",
      what: "Smart to-do list of what needs your attention",
      how: "Shows setup tasks (connect accounts, define brand), pending approvals, leads without outreach, posts due soon",
      example: "Reminds you: '3 leads have no outreach drafted yet' → you know what to tackle next",
    },
    {
      name: "Growth Analytics",
      emoji: "📈",
      what: "Shows your LinkedIn performance + AI insights",
      how: "Connects to LinkedIn → pulls your metrics → AI analyzes: 'What's working? What isn't? What to try next?'",
      example: "Analytics says 'Threads get 3x engagement, single posts get 1x' → you write more threads",
    },
  ];

  return (
    <div>
      <p style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "16px", lineHeight: "1.6" }}>
        While your content runs on autopilot, 5 AI agents gather market intelligence and surface opportunities. Use this intel to make smarter content decisions.
      </p>

      <div style={{ display: "grid", gap: "12px" }}>
        {agents.map((agent, idx) => (
          <div
            key={idx}
            style={{
              background: "var(--card)",
              border: "1px solid var(--line)",
              borderRadius: "8px",
              padding: "14px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
              <span style={{ fontSize: "20px" }}>{agent.emoji}</span>
              <div>
                <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--ink)", margin: 0 }}>
                  {agent.name}
                </p>
                <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                  {agent.what}
                </p>
              </div>
            </div>

            <div style={{ paddingLeft: "30px" }}>
              <p style={{ fontSize: "12px", color: "var(--muted)", margin: "6px 0", lineHeight: "1.5" }}>
                <strong>How it works:</strong> {agent.how}
              </p>
              <p style={{ fontSize: "12px", color: "var(--teal-deep)", margin: 0, lineHeight: "1.5" }}>
                <strong>Example:</strong> {agent.example}
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
        <p style={{ fontSize: "12px", color: "var(--teal-deep)", margin: 0, lineHeight: "1.5" }}>
          <strong>🎯 Why this matters:</strong> You could create random content, or you could use real market data to create content that actually resonates. These 5 agents are your competitive advantage.
        </p>
      </div>
    </div>
  );
}
