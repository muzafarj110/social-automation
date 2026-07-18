export default function WhatsAppGuide() {
  return (
    <div>
      <p style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "16px", lineHeight: "1.6" }}>
        WhatsApp agent turns your business WhatsApp number into a 24/7 AI customer service bot. It answers common questions instantly, even at 3am.
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
              Setup (one-time, 15-30 minutes)
            </p>
          </div>
          <div style={{ paddingLeft: "38px", display: "grid", gap: "8px" }}>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Go to WhatsApp agent → Settings tab
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>6-step setup wizard guides you through connecting Meta App</p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Create Meta Developer App (free account)
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>Follow the wizard. Takes 10 minutes to set up Meta account + get your credentials.</p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Configure webhook in Meta's dashboard
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>App shows you the URL + token. Paste into Meta dashboard. That's it.</p>
            </div>
          </div>
        </div>

        {/* Knowledge Base Section */}
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
              Build your FAQ knowledge base
            </p>
          </div>
          <div style={{ paddingLeft: "38px", display: "grid", gap: "8px" }}>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Go to Knowledge base tab → Add Q&A entries
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                Q: "What's your pricing?" A: "We have 3 plans: Free ($0), Pro ($29/mo), Enterprise ($99/mo)"
              </p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Add anything customers commonly ask
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                Pricing, policies, features, hours, refunds, setup, troubleshooting, etc.
              </p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Save FAQ
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                AI reads this knowledge base to answer customer questions. Only answers from what's here.
              </p>
            </div>
          </div>
        </div>

        {/* How It Works Section */}
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
              3
            </div>
            <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--ink)", margin: 0 }}>
              How it works (24/7 automatic)
            </p>
          </div>
          <div style={{ paddingLeft: "38px", display: "grid", gap: "8px" }}>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Customer sends a message to your WhatsApp
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                "Hi, do you have a free trial?"
              </p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                AI reads your FAQ + their message
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                Instantly drafts a response based on what you told it
              </p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                AI sends reply (in &lt;5 seconds)
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                "Yes! We offer a free 14-day trial with 50 credits. No credit card required."
              </p>
            </div>
            <div>
              <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 2px" }}>
                Sensitive topics get flagged for you
              </p>
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0 }}>
                If customer mentions "refund", "complaint", "legal", etc., you get a notification so you can follow up personally
              </p>
            </div>
          </div>
        </div>

        {/* Real Example */}
        <div
          style={{
            background: "var(--teal-tint)",
            border: "1px solid var(--teal)",
            borderRadius: "8px",
            padding: "12px 14px",
          }}
        >
          <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--teal-deep)", margin: "0 0 6px" }}>
            📲 Real Conversation:
          </p>
          <div style={{ fontSize: "11px", color: "var(--teal-deep)", lineHeight: "1.8", margin: 0 }}>
            <p style={{ margin: "0 0 4px" }}>
              <strong>Customer (3:47 AM):</strong> "Hi! Are you still in beta?"
            </p>
            <p style={{ margin: "0 0 4px" }}>
              <strong>AI (3:47 AM):</strong> "Hi! Yes, we're in beta. All customers get free early access + 50 free credits. Want to try it?"
            </p>
            <p style={{ margin: "0 0 4px" }}>
              <strong>Customer (3:52 AM):</strong> "Cool! What payment methods do you accept?"
            </p>
            <p style={{ margin: 0 }}>
              <strong>AI (3:52 AM):</strong> "We accept all major credit cards + PayPal. You can also request invoice billing for annual plans."
            </p>
          </div>
        </div>

        {/* Tips Section */}
        <div style={{ background: "var(--card)", border: "1px solid var(--line)", borderRadius: "8px", padding: "12px 14px" }}>
          <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--ink)", margin: "0 0 8px" }}>
            💡 Tips:
          </p>
          <ul style={{ fontSize: "11px", color: "var(--muted)", lineHeight: "1.6", margin: 0, paddingLeft: "20px" }}>
            <li>Start with your top 10 FAQ questions. Add more as you see customer patterns.</li>
            <li>Update FAQ quarterly as your product changes.</li>
            <li>Review "Flagged conversations" tab weekly to see what questions weren't covered in FAQ.</li>
            <li>Costs 1 credit per AI response (same as LinkedIn outreach). Budget accordingly.</li>
            <li>Works for customer service + lead generation simultaneously.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
