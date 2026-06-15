import { useEffect, useState } from "react";
import { listOpportunities } from "../api.js";

const IMPACT = {
  high: { label: "High impact", cls: "published" },
  medium: { label: "Medium", cls: "pending" },
  low: { label: "Low", cls: "draft" },
};

// AI marketing team's "what to act on next", derived from the user's own data.
export default function Opportunities({ goTab }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    listOpportunities().then(setData).catch((e) => setErr(e.message));
  }, []);

  if (err) return <div className="error">{err}</div>;
  if (!data) return <div className="empty">Scanning for opportunities…</div>;

  const ops = data.opportunities || [];

  return (
    <>
      <div className="card aicard">
        <div className="row" style={{ alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0 }}>Opportunities</h2>
            <p className="muted" style={{ margin: "4px 0 0" }}>
              Your AI marketing team watches your data and flags what to act on next.
            </p>
          </div>
          <div className="spacer" />
          <span className="badge published">{ops.length} found</span>
        </div>
      </div>

      {ops.length === 0 ? (
        <div className="empty">You're all caught up — nothing pressing right now.</div>
      ) : (
        <div className="masonry">
          {ops.map((o) => {
            const imp = IMPACT[o.impact] || IMPACT.medium;
            return (
              <div className="card" key={o.id}>
                <div className="row" style={{ alignItems: "center", marginBottom: 8 }}>
                  <span className="badge kind">{o.tag}</span>
                  <div className="spacer" />
                  <span className={`badge ${imp.cls}`}>{imp.label}</span>
                </div>
                <div style={{ fontWeight: 700, fontSize: 15, color: "var(--ink)" }}>{o.title}</div>
                <p className="muted" style={{ margin: "6px 0 14px", lineHeight: 1.5 }}>{o.desc}</p>
                <button className="btn-primary" onClick={() => goTab(o.action_tab)}>
                  {o.action_label} →
                </button>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
