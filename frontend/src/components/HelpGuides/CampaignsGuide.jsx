export default function CampaignsGuide() {
  return (
    <div>
      <p style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "16px", lineHeight: "1.6" }}>
        Campaigns let you automate content generation. Set it once, AI generates fresh posts on a schedule forever. No more "what should I post today?"
      </p>

      <div style={{ display: "grid", gap: "14px" }}>
        {/* Setup Section */}
        <div style={{ background: "var(--card)", border: "1px solid var(--line)", borderRadius: "8px", padding: "14px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                background: "var(--teal)",
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "14px",
                fontWeight: 600,
              }}
            >
              1
            </div>
            <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--ink)", margin: 0 }}>
              Setup (one-time, 5 minutes)
            </p>
          </div>
          <div style={{ paddingLeft: "38px", display: "grid", gap: "8px" }}>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Go to Campaigns → Click "Create campaign"
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>Name it, pick which platforms, set posting frequency (e.g., 3x per week)</p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Enter 2-3 topics AI should generate about
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                Example: "SaaS growth tactics", "AI productivity hacks", "Founder lessons learned"
              </p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Choose approval mode
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                "Approve first" = you review before posting, OR "Auto-publish" = posts go live immediately
              </p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Click "Start campaign"
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>That's it. Your campaign is now running.</p>
            </div>
          </div>
        </div>

        {/* Automation Section */}
        <div style={{ background: "var(--card)", border: "1px solid var(--line)", borderRadius: "8px", padding: "14px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                background: "var(--teal)",
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "14px",
                fontWeight: 600,
              }}
            >
              2
            </div>
            <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--ink)", margin: 0 }}>
              Runs automatically (24/7)
            </p>
          </div>
          <div style={{ paddingLeft: "38px", display: "grid", gap: "8px" }}>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Every 15 minutes, AI checks: "Is there a post due today?"
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                If yes → AI generates a fresh post about one of your topics
              </p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Posts appear in your Inbox (if "Approve first") or go live immediately
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                Each post is unique, on-brand, tailored to your audience
              </p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Posts publish to all your connected platforms at your chosen time
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                LinkedIn, Twitter, Instagram, TikTok, Facebook — all at once, auto-formatted
              </p>
            </div>
          </div>
        </div>

        {/* Example Section */}
        <div
          style={{
            background: "var(--teal-tint)",
            border: "1px solid var(--teal)",
            borderRadius: "8px",
            padding: "12px 14px",
          }}
        >
          <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--teal-deep)", margin: "0 0 6px" }}>
            📋 Real Example:
          </p>
          <p style={{ fontSize: "11px", color: "var(--teal-deep)", lineHeight: "1.6", margin: 0 }}>
            You create a campaign called "SaaS Growth" with topics: "pricing strategies", "customer retention", "scaling tips". Set it to 3x per week.
            <br />
            <br />
            Week 1: AI generates posts on Mon, Wed, Fri. Each is unique, on-brand.
            <br />
            Week 2-52: Same thing happens automatically. You never think about it.
            <br />
            <br />
            Result: 156 posts/year with zero effort after day 1. Consistent presence = visibility = growth.
          </p>
        </div>

        {/* Tips Section */}
        <div style={{ background: "var(--card)", border: "1px solid var(--line)", borderRadius: "8px", padding: "12px 14px" }}>
          <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 8px" }}>
            💡 Pro Tips:
          </p>
          <ul style={{ fontSize: "11px", color: "var(--muted)", lineHeight: "1.6", margin: 0, paddingLeft: "20px" }}>
            <li>Start with "Approve first" mode. Once you trust the output, switch to "Auto-publish".</li>
            <li>Mix 3-5 topics so posts feel varied, not repetitive.</li>
            <li>You can edit or delete any post before it publishes. Full control.</li>
            <li>Run multiple campaigns simultaneously (one for sales content, one for thought leadership, etc.)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
