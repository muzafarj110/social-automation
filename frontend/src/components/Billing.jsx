import { useEffect, useState } from "react";
import { getBilling, startCheckout, openBillingPortal } from "../api.js";

const TIER_FEATURES = [
  "Posts across all 15 platforms",
  "AI brand voice & autopilot",
  "Approve-first publishing",
  "Analytics & learning loop",
];
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
      {err && <div className="flash error">{err}</div>}

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
        <h2>{active ? "Change your plan" : "Choose your plan"}</h2>
        {!data ? (
          <div className="empty">Loading…</div>
        ) : !data.subscriptions_enabled ? (
          <div className="empty">Plans aren't switched on yet. Once Stripe is configured, they appear here.</div>
        ) : data.plans.length === 0 ? (
          <div className="empty">No plans are set up yet.</div>
        ) : (
          <div className="pricing-grid">
            {data.plans.map((p, i) => {
              const featured = data.plans.length > 1 && i === Math.floor(data.plans.length / 2);
              const current = active && sub.tier === p.tier;
              return (
                <div className={`tier${featured ? " featured" : ""}`} key={p.price_id}>
                  {featured && <span className="badge-pop">Most popular</span>}
                  <div className="accent" />
                  <div className="name">{cap(p.tier)}</div>
                  <div className="amt">{p.credits.toLocaleString()}</div>
                  <div className="unit">credits / month</div>
                  <ul>{TIER_FEATURES.map((f) => <li key={f}>{f}</li>)}</ul>
                  <div className="pick">
                    <button className="btn-primary" style={{ width: "100%" }}
                      disabled={busy || current} onClick={() => buy(p.price_id)}>
                      {current ? "Current plan" : "Get this plan"}
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
