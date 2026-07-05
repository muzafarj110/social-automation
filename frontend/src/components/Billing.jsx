import { useEffect, useState } from "react";
import { getBilling, startCheckout, openBillingPortal } from "../api.js";

const TIER_DATA = {
  free: {
    price: "$0",
    label: "Free",
    included: [
      "30 credits / day — no card needed",
      "Quick post generator (1 cr)",
      "Content agent drafts (1 cr)",
      "Competitor analysis (1 cr)",
      "Social listening scans (1 cr)",
      "Lead-gen outreach drafts (1 cr)",
      "Opportunities refresh (1 cr)",
      "WhatsApp + Telegram cross-posting",
      "Post calendar and scheduling",
    ],
    excluded: [
      "Always-on Campaigns",
      "Studio images (5 cr each)",
      "SEO + GEO deep analysis (2 cr)",
    ],
  },
  starter: {
    price: "$29",
    label: "Starter",
    included: [
      "Content agent — drafts and posts",
      "Quick post generator",
      "Competitor agent (1 rival)",
      "Post calendar",
      "WhatsApp + Telegram cross-posting",
    ],
    excluded: [
      "Always-on Campaigns",
      "SEO + GEO agent",
      "Studio images and carousels",
    ],
  },
  growth: {
    price: "$79",
    label: "Growth",
    popular: true,
    included: [
      "Everything in Starter",
      "Always-on Campaigns — set and forget posting",
      "SEO + GEO agent",
      "Social listening agent",
      "Lead-gen agent",
      "Opportunities agent",
    ],
    excluded: [
      "Studio agent (images, carousels)",
      "Multi-client workspaces",
    ],
  },
  pro: {
    price: "$149",
    label: "Pro",
    included: [
      "Everything in Growth",
      "Studio agent — images, carousels, newsletters",
      "Brand strategist agent",
      "Multi-client workspaces",
      "Unlimited competitor tracking",
      "Priority support",
      "Credit top-ups available",
    ],
    excluded: [],
  },
};

const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

export default function Billing({ user }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getBilling().then(setData).catch((e) => setErr(e.message));
  }, []);

  const go = async (fn) => {
    setErr(""); setBusy(true);
    try {
      const res = await fn();
      if (res?.url) window.location.href = res.url;
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };
  const buy = (price_id) => go(() => startCheckout(price_id));
  const manage = () => go(() => openBillingPortal());

  const credits = data?.credits ?? user?.credits ?? 0;
  const sub = data?.subscription;
  const active = sub && sub.tier && sub.status !== "canceled";

  return (
    <>
      {err && <div className="flash error" role="alert">{err}</div>}

      <div className="card">
        <h2>Your plan</h2>
        {active ? (
          <div className="row" style={{ alignItems: "center" }}>
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, color: "var(--teal)" }}>
                {cap(sub.tier)}
                <span className={`badge ${sub.status === "active" ? "published" : "pending"}`}
                  style={{ marginLeft: 10, verticalAlign: "middle" }}>{sub.status}</span>
              </div>
              <p className="muted" style={{ margin: "4px 0 0" }}>
                {sub.renews_at
                  ? `Renews ${new Date(sub.renews_at).toLocaleDateString()}`
                  : "Active subscription"} · credits reset each cycle.
              </p>
            </div>
            <div className="spacer" />
            <button className="btn-secondary" disabled={busy} onClick={manage}>Manage plan</button>
          </div>
        ) : data?.free ? (
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, color: "var(--teal)" }}>Free trial</div>
            <p className="muted" style={{ margin: "4px 0 0" }}>
              {data.free.trial_expired
                ? "Your free trial has ended — subscribe below to keep creating."
                : `${data.free.remaining_today} of ${data.free.daily_limit} free credits left today`
                  + (data.free.trial_ends_at ? ` · trial ends ${new Date(data.free.trial_ends_at).toLocaleDateString()}` : "")}
            </p>
          </div>
        ) : (
          <p className="muted" style={{ margin: 0 }}>You're on the free plan. Pick a plan below.</p>
        )}
      </div>

      <div className="card">
        <h2>{active ? "Credits" : "Free credits today"}</h2>
        <div style={{ fontSize: 40, fontWeight: 800, color: "var(--teal)" }}>
          {active ? credits : (data?.free?.remaining_today ?? 0)}
          {!active && data?.free && <span style={{ fontSize: 18, color: "var(--muted)" }}> / {data.free.daily_limit}</span>}
        </div>
        <p className="muted" style={{ marginTop: 4 }}>
          {active
            ? "Each AI action — a generated post, or each post a campaign produces — uses 1 credit."
            : "Free credits reset daily during your trial. Subscribe for a larger monthly allowance."}
          {user?.is_admin ? " As an admin, your usage is unlimited." : ""}
        </p>
      </div>

      <div className="card">
        <h2>What a credit buys</h2>
        <p className="muted" style={{ marginTop: -4, marginBottom: 10 }}>
          Same cost table on every plan — only the monthly credit allowance changes.
        </p>
        <div className="row" style={{ flexWrap: "wrap", gap: 16 }}>
          {[
            ["1 credit", "Text posts, drafts, competitor/listening/lead-gen scans"],
            ["2 credits", "Long-form content — articles, newsletters, sequences"],
            ["5 credits", "Image generation — social cards, ad creatives, infographics"],
            ["15 credits", "Video generation — short + long cut, both at once"],
          ].map(([cost, desc]) => (
            <div key={cost} style={{ minWidth: 180 }}>
              <div style={{ fontWeight: 700, color: "var(--teal)" }}>{cost}</div>
              <div className="muted" style={{ fontSize: 13 }}>{desc}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>{active ? "Change your plan" : "Choose your plan"}</h2>
        {!data ? (
          <div className="empty">Loading…</div>
        ) : (
          <div className="pricing-grid">
            {/* Free tier — always shown regardless of Stripe config */}
            {(() => {
              const meta = TIER_DATA.free;
              const current = !active;
              return (
                <div className="tier" key="free">
                  <div className="accent" />
                  <div className="name">{meta.label}</div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 4, margin: "6px 0 2px" }}>
                    <span className="amt">{meta.price}</span>
                    <span className="unit" style={{ fontSize: 13 }}>/mo</span>
                  </div>
                  <div className="unit">30 credits / day · 180 day trial</div>
                  <ul style={{ marginTop: 12 }}>
                    {meta.included.map((f) => (
                      <li key={f} style={{ color: "var(--ink)" }}>
                        <span style={{ color: "var(--teal)", marginRight: 6 }}>✓</span>{f}
                      </li>
                    ))}
                    {meta.excluded.map((f) => (
                      <li key={f} style={{ color: "var(--muted)", listStyle: "none" }}>
                        <span style={{ marginRight: 6 }}>–</span>{f}
                      </li>
                    ))}
                  </ul>
                  <div className="pick">
                    <button className="btn-primary" style={{ width: "100%", opacity: current ? 0.6 : 1 }} disabled={current}>
                      {current ? "Current plan" : "Downgrade"}
                    </button>
                  </div>
                </div>
              );
            })()}
            {data.subscriptions_enabled && data.plans.map((p) => {
              const meta = TIER_DATA[p.tier] || {};
              const current = active && sub.tier === p.tier;
              const featured = meta.popular;
              return (
                <div className={`tier${featured ? " featured" : ""}`} key={p.price_id}>
                  {featured && <span className="badge-pop">Most popular</span>}
                  <div className="accent" />
                  <div className="name">{meta.label || cap(p.tier)}</div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 4, margin: "6px 0 2px" }}>
                    <span className="amt">{meta.price || ""}</span>
                    <span className="unit" style={{ fontSize: 13 }}>/mo</span>
                  </div>
                  <div className="unit">{p.credits.toLocaleString()} credits / month</div>
                  <ul style={{ marginTop: 12 }}>
                    {(meta.included || []).map((f) => (
                      <li key={f} style={{ color: "var(--ink)" }}>
                        <span style={{ color: "var(--teal)", marginRight: 6 }}>✓</span>{f}
                      </li>
                    ))}
                    {(meta.excluded || []).map((f) => (
                      <li key={f} style={{ color: "var(--muted)", listStyle: "none" }}>
                        <span style={{ marginRight: 6 }}>–</span>{f}
                      </li>
                    ))}
                  </ul>
                  <div className="pick">
                    <button className="btn-primary" style={{ width: "100%" }}
                      disabled={busy || current} onClick={() => buy(p.price_id)}>
                      {current ? "Current plan" : "Get started"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <p className="muted" style={{ fontSize: 12, marginTop: 12 }}>
          Secure checkout & billing are handled by Stripe. We never see or store your card details.
        </p>
      </div>

      {data?.packs?.length > 0 && (
        <div className="card">
          <h2>Need more this month?</h2>
          <p className="muted" style={{ marginTop: -4 }}>One-time credit top-ups — added on top of your balance right away.</p>
          <div className="pack-grid">
            {data.packs.map((p) => (
              <div className="pack-card" key={p.price_id}>
                <div className="credits">{p.credits.toLocaleString()}</div>
                <div className="unit">credits</div>
                <button className="btn-secondary" disabled={busy} onClick={() => buy(p.price_id)}>
                  Buy
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
