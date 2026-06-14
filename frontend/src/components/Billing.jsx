import { useEffect, useState } from "react";
import { getBilling, startCheckout } from "../api.js";

export default function Billing({ user }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getBilling().then(setData).catch((e) => setErr(e.message));
  }, []);

  const buy = async (price_id) => {
    setErr(""); setBusy(true);
    try {
      const res = await startCheckout(price_id);
      if (res?.url) window.location.href = res.url;   // off to Stripe Checkout
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const credits = data?.credits ?? user?.credits ?? 0;

  return (
    <>
      {err && <div className="flash error">{err}</div>}

      <div className="card">
        <h2>Your credits</h2>
        <div style={{ fontSize: 40, fontWeight: 800, color: "#7c5cfc" }}>{credits}</div>
        <p className="muted" style={{ marginTop: 4 }}>
          Each AI action — a generated post, or each post a campaign produces — uses 1 credit.
          {user?.is_admin ? " As an admin, your usage is unlimited." : ""}
        </p>
      </div>

      <div className="card">
        <h2>Buy more credits</h2>
        {!data ? (
          <div className="empty">Loading…</div>
        ) : !data.enabled ? (
          <div className="empty">
            Billing isn't switched on yet. Once Stripe is configured, credit packs appear here.
          </div>
        ) : data.packs.length === 0 ? (
          <div className="empty">No credit packs are set up yet.</div>
        ) : (
          <div className="pill-list" style={{ marginTop: 8 }}>
            {data.packs.map((p) => (
              <div className="pill" key={p.price_id} style={{ alignItems: "center" }}>
                <strong>{p.credits.toLocaleString()} credits</strong>
                <div className="spacer" />
                <button className="btn-primary" disabled={busy} onClick={() => buy(p.price_id)}>
                  Buy
                </button>
              </div>
            ))}
          </div>
        )}
        <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>
          Secure checkout is handled by Stripe. We never see or store your card details.
        </p>
      </div>
    </>
  );
}
