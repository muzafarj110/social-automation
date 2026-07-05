import { useState } from "react";
import { TIER_DATA, TIER_ORDER } from "../constants/pricing.js";

// Public marketing site. `onStart` opens the auth screen in register mode,
// `onLogin` in login mode. Copy is original; structure mirrors a modern
// AI-marketing landing page (hero → how → benefits → features → capabilities
// → why → testimonials → security → CTA → footer).

const STEPS = [
  { t: "Connect & personalize", d: "Link your channels and tell your team about your brand. They learn your voice in minutes." },
  { t: "Direct, automate or consult", d: "Hand over a goal, set it on autopilot, or just chat — your team figures out the rest." },
  { t: "Runs 24/7, no breaks", d: "Agents research, write, schedule and engage around the clock, getting smarter every day." },
  { t: "Review & approve", d: "Everything lands in your work feed. Approve with one tap, or let trusted tasks run themselves." },
];

const BENEFITS = [
  { i: "↗", t: "Scale without the overhead", d: "Get the output of a full marketing team — strategy, content, SEO, outreach — without the headcount or the cost." },
  { i: "⚡", t: "Results from day one", d: "Your agents act on real-time data immediately. No long onboarding, no agency ramp-up." },
  { i: "◎", t: "All your work in one place", d: "Plan, create, publish, engage and measure across every platform from a single workspace." },
];

const FEATURES = [
  { i: "✦", t: "Your expert AI team", d: "Specialist agents — content, SEO, competitor, lead-gen and more — each focused on what it does best." },
  { i: "≡", t: "Live work feed", d: "A running stream of what your agents are doing. Review, edit and approve in seconds." },
  { i: "◗", t: "Chat to get it done", d: "Brief the whole team in plain language. No menus, no setup — just tell them what you want." },
  { i: "▦", t: "Custom dashboards", d: "Build the views you care about with a flexible block editor tailored to your goals." },
  { i: "↻", t: "Learns and grows daily", d: "Every result feeds back in. Your team gets sharper and more on-brand the longer you use it." },
  { i: "⚇", t: "Collaborate easily", d: "Role-based access and shareable views for teammates, clients and stakeholders." },
];

const CAPS = {
  social: {
    label: "Social media", h: "Grow your audience on social",
    p: "Your content agent studies trends, writes on-brand posts for every platform and schedules them at the right time — then engages with the people who matter.",
    pts: ["AI-written, on-brand posts", "Per-platform formatting & hashtags", "Smart scheduling across 15 channels", "Auto-drafted replies you approve"],
  },
  seo: {
    label: "SEO", h: "Own the search results",
    p: "Keyword research, content optimization and on-page fixes, continuously — so the right people find you on Google.",
    pts: ["Keyword & gap research", "Content optimization", "On-page recommendations", "Rank tracking over time"],
  },
  geo: {
    label: "GEO", h: "Get recommended by AI",
    p: "As people ask ChatGPT and Claude for recommendations, your GEO agent works to make sure your brand is the answer.",
    pts: ["AI-answer visibility", "Entity & citation building", "Local presence optimization", "Prompt-coverage tracking"],
  },
  competitor: {
    label: "Competitor", h: "Always one step ahead",
    p: "Real-time monitoring of your competitors' moves — so you can copy what's working and act on the gaps they leave open.",
    pts: ["Live competitor monitoring", "Winning-tactic detection", "Positioning gap alerts", "Actionable playbooks"],
  },
};

const SECURITY = [
  { i: "⚿", t: "Your tokens stay yours", d: "Connected-account credentials are encrypted at rest and never exposed to third parties." },
  { i: "⚙", t: "Full control over roles", d: "Decide exactly who on your team can see and do what, with granular permissions." },
  { i: "⛉", t: "No training on your data", d: "Third-party AI providers never store or learn from your information. Your data is yours." },
];

function Mono({ bg, fg, children }) {
  return <span className="mono" style={{ background: bg, color: fg }}>{children}</span>;
}

const LEGAL_NOTE = {
  Privacy: "We're finalizing our Privacy Policy. In the meantime, please reach out with any questions and we'll be happy to help.",
  Terms: "We're finalizing our Terms of Service. In the meantime, please reach out with any questions and we'll be happy to help.",
};

export default function Landing({ onStart, onLogin }) {
  const [cap, setCap] = useState("social");
  const [legalOpen, setLegalOpen] = useState(null); // "Privacy" | "Terms" | null
  const c = CAPS[cap];

  return (
    <div className="lp">
      {/* nav */}
      <nav className="lp-nav">
        <div className="lp-wrap lp-nav-inner">
          <div className="lp-logo"><span className="mark">A</span> Autopilot</div>
          <div className="lp-links">
            <a onClick={() => document.getElementById("features")?.scrollIntoView({ behavior: "smooth" })}>Features</a>
            <a onClick={() => document.getElementById("capabilities")?.scrollIntoView({ behavior: "smooth" })}>Capabilities</a>
            <a onClick={() => document.getElementById("how")?.scrollIntoView({ behavior: "smooth" })}>How it works</a>
            <a onClick={() => document.getElementById("security")?.scrollIntoView({ behavior: "smooth" })}>Security</a>
          </div>
          <div className="lp-nav-cta">
            <span className="lp-ghostlink" onClick={onLogin}>Log in</span>
            <button className="lp-btn lp-btn-primary" onClick={onStart}>Start for free</button>
          </div>
        </div>
      </nav>

      {/* hero */}
      <header className="lp-wrap lp-hero">
        <div className="lp-eyebrow"><span className="pip" /> Your AI marketing team · working 24/7</div>
        <h1 className="lp-h1">Your personal AI marketing team. <span className="acc">Taking initiative 24/7.</span></h1>
        <p className="lp-sub">
          An all-in-one team of AI agents that proactively runs your marketing — planning, writing,
          publishing, engaging and learning. It knows how you work and gets smarter every day.
        </p>
        <div className="lp-hero-cta">
          <button className="lp-btn lp-btn-primary lp-btn-lg" onClick={onStart}>Start your free trial</button>
          <button className="lp-btn lp-btn-ghost lp-btn-lg" onClick={() => document.getElementById("how")?.scrollIntoView({ behavior: "smooth" })}>See how it works</button>
        </div>
        <div className="lp-hero-note">No card required · Launch in minutes</div>

        {/* product mock */}
        <div className="lp-mock">
          <div className="lp-mock-bar"><span className="d" /><span className="d" /><span className="d" /></div>
          <div className="lp-mock-body">
            <div className="lp-mock-side">
              <div className="si on"><span className="sd" /> Live work feed</div>
              <div className="si"><span className="sd" /> Content agent</div>
              <div className="si"><span className="sd" /> Always-on Campaigns</div>
              <div className="si"><span className="sd" /> Competitor agent</div>
              <div className="si idle"><span className="sd" /> SEO + GEO</div>
              <div className="si idle"><span className="sd" /> Lead-gen agent</div>
            </div>
            <div className="lp-mock-main">
              <div className="lp-mock-chat">Tell your team what to focus on this week… <span className="send">↑</span></div>
              <div className="lp-mock-card">
                <div className="mh"><Mono bg="#e1f5ee" fg="#0F6E56">Co</Mono> Content agent · drafted 3 posts · 2m ago</div>
                <div className="mt">“The hidden cost of hiring before you've found product-market fit…”</div>
              </div>
              <div className="lp-mock-card">
                <div className="mh"><Mono bg="#eeedfe" fg="#534AB7">Cp</Mono> Competitor agent · found a winning tactic · 18m ago</div>
                <div className="mt">Rival launched a free audit lead magnet — suggest we match it.</div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* how it works */}
      <section id="how" className="lp-sec tint">
        <div className="lp-wrap">
          <div className="lp-kicker">How it works</div>
          <h2 className="lp-h2">Launch your autonomous team in four steps</h2>
          <p className="lp-lead">It works on its own and evolves every day — you stay in control with approve-first by default.</p>
          <div className="lp-grid c4">
            {STEPS.map((s, i) => (
              <div className="lp-card" key={i}>
                <div className="lp-step-n">STEP {i + 1}</div>
                <h3>{s.t}</h3><p>{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* benefits */}
      <section className="lp-sec">
        <div className="lp-wrap">
          <div className="lp-kicker">Why teams switch</div>
          <h2 className="lp-h2">The smartest way to grow</h2>
          <div className="lp-grid c3">
            {BENEFITS.map((b) => (
              <div className="lp-card" key={b.t}>
                <div className="lp-ic">{b.i}</div>
                <h3>{b.t}</h3><p>{b.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* features */}
      <section id="features" className="lp-sec tint">
        <div className="lp-wrap">
          <div className="lp-kicker">The platform</div>
          <h2 className="lp-h2">Everything you need to get results</h2>
          <p className="lp-lead">Manage your AI team, your data and your workflows in one single place.</p>
          <div className="lp-grid c3">
            {FEATURES.map((f) => (
              <div className="lp-card" key={f.t}>
                <div className="lp-ic">{f.i}</div>
                <h3>{f.t}</h3><p>{f.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* capabilities (tabbed) */}
      <section id="capabilities" className="lp-sec">
        <div className="lp-wrap">
          <div className="lp-kicker">Capabilities</div>
          <h2 className="lp-h2">One team, unlimited marketing expertise</h2>
          <p className="lp-lead">From deep strategy to high-speed execution — your team activates the right skill for the job.</p>
          <div className="lp-tabs">
            {Object.entries(CAPS).map(([k, v]) => (
              <button key={k} className={`lp-tab ${cap === k ? "on" : ""}`} onClick={() => setCap(k)}>{v.label}</button>
            ))}
          </div>
          <div className="lp-cap-panel">
            <div>
              <h3>{c.h}</h3>
              <p>{c.p}</p>
              <ul className="lp-cap-list">{c.pts.map((p) => <li key={p}>{p}</li>)}</ul>
              <button className="lp-btn lp-btn-ghost" style={{ marginTop: 20 }} onClick={onStart}>Try {c.label} free →</button>
            </div>
            <div className="lp-cap-visual">
              <div className="lp-mock-chat" style={{ borderRadius: 12 }}>{c.label} agent working… <span className="send">✦</span></div>
              {c.pts.slice(0, 3).map((p, i) => (
                <div className="lp-mock-card" key={i}><div className="mt">✓ {p}</div></div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* why different */}
      <section className="lp-sec tint">
        <div className="lp-wrap">
          <div className="lp-kicker">Why Autopilot is different</div>
          <h2 className="lp-h2">Built for results, not just output</h2>
          <div className="lp-why">
            <div><div className="n">01</div><h3>From start to finish</h3><p>Most tools give you a draft. Your team takes a goal all the way to a published, measured result.</p></div>
            <div><div className="n">02</div><h3>Backed by real data</h3><p>Decisions come from your live analytics and the market — not generic best-practice guesses.</p></div>
            <div><div className="n">03</div><h3>Personalized, not generic</h3><p>It connects your data, works as a team and learns from every outcome to stay unmistakably you.</p></div>
          </div>
        </div>
      </section>

      {/* pricing */}
      <section id="pricing" className="lp-sec">
        <div className="lp-wrap">
          <div className="lp-kicker">Simple pricing</div>
          <h2 className="lp-h2">Free to start. Upgrade when you're ready.</h2>
          <div className="pricing-grid">
            {TIER_ORDER.map((key) => {
              const meta = TIER_DATA[key];
              return (
                <div className={`tier${meta.popular ? " featured" : ""}`} key={key}>
                  {meta.popular && <span className="badge-pop">Most popular</span>}
                  <div className="accent" />
                  <div className="name">{meta.label}</div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 4, margin: "6px 0 2px" }}>
                    <span className="amt">{meta.price}</span><span className="unit" style={{ fontSize: 13 }}>/mo</span>
                  </div>
                  {meta.note && <div className="unit">{meta.note}</div>}
                  <ul style={{ marginTop: 12 }}>
                    {meta.included.map((f) => <li key={f}><span style={{ color: "var(--teal)", marginRight: 6 }}>✓</span>{f}</li>)}
                    {meta.excluded.map((f) => <li key={f} style={{ color: "var(--muted)", listStyle: "none" }}><span style={{ marginRight: 6 }}>–</span>{f}</li>)}
                  </ul>
                  <div className="pick">
                    <button className="lp-btn lp-btn-primary" style={{ width: "100%" }} onClick={onStart}>
                      {key === "free" ? "Start for free" : `Choose ${meta.label}`}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
          <p className="lp-hero-note" style={{ textAlign: "center" }}>No card required to start.</p>
        </div>
      </section>

      {/* security */}
      <section id="security" className="lp-sec tint">
        <div className="lp-wrap">
          <div className="lp-kicker">Security first</div>
          <h2 className="lp-h2">Your data stays secure and private</h2>
          <div className="lp-grid c3">
            {SECURITY.map((s) => (
              <div className="lp-card" key={s.t}>
                <div className="lp-ic">{s.i}</div>
                <h3>{s.t}</h3><p>{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* final cta */}
      <section className="lp-sec">
        <div className="lp-wrap">
          <div className="lp-cta">
            <h2>Save time, cut costs, and drive better results.</h2>
            <p>Let your AI team handle the work, centralize your marketing, and improve results every day.</p>
            <button className="lp-btn lp-btn-primary lp-btn-lg" onClick={onStart}>Start your free trial</button>
          </div>
        </div>
      </section>

      {/* footer */}
      <footer className="lp-foot">
        <div className="lp-wrap">
          <div className="lp-foot-grid">
            <div>
              <div className="lp-logo"><span className="mark">A</span> Autopilot</div>
              <p className="blurb">Your AI marketing team — planning, creating, publishing and learning, 24/7.</p>
            </div>
            <div>
              <h4>Product</h4>
              <a onClick={() => document.getElementById("features")?.scrollIntoView({ behavior: "smooth" })}>Features</a>
              <a onClick={() => document.getElementById("capabilities")?.scrollIntoView({ behavior: "smooth" })}>Capabilities</a>
              <a onClick={() => document.getElementById("pricing")?.scrollIntoView({ behavior: "smooth" })}>Pricing</a>
            </div>
            <div>
              <h4>Company</h4>
              <a onClick={onStart}>Get started</a>
              <a onClick={() => document.getElementById("how")?.scrollIntoView({ behavior: "smooth" })}>How it works</a>
              <a onClick={() => document.getElementById("security")?.scrollIntoView({ behavior: "smooth" })}>Security</a>
            </div>
            <div>
              <h4>Legal</h4>
              <a onClick={() => setLegalOpen("Privacy")}>Privacy</a>
              <a onClick={() => setLegalOpen("Terms")}>Terms</a>
            </div>
          </div>
          <div className="lp-foot-bottom">© 2026 Autopilot. All rights reserved.</div>
        </div>
      </footer>

      {/* legal placeholder modal (real Privacy/Terms pages pending legal review) */}
      {legalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          onClick={() => setLegalOpen(null)}
          style={{ position: "fixed", inset: 0, background: "rgba(16,24,40,0.45)", display: "grid", placeItems: "center", zIndex: 1000, padding: 20 }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ background: "#fff", borderRadius: 16, padding: "28px 26px", maxWidth: 380, width: "100%", boxShadow: "var(--shadow-lift, 0 20px 50px rgba(16,24,40,0.2))" }}
          >
            <h3 style={{ margin: "0 0 10px", fontSize: 18, fontWeight: 700, color: "var(--ink)" }}>{legalOpen}</h3>
            <p style={{ margin: 0, fontSize: 14.5, color: "#475467", lineHeight: 1.6 }}>{LEGAL_NOTE[legalOpen]}</p>
            <button className="lp-btn lp-btn-primary" style={{ marginTop: 20 }} onClick={() => setLegalOpen(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
