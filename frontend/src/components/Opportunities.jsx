import { useEffect, useState } from "react";
import { listOpportunities } from "../api.js";

const IMPACT = {
  high:   { label: "High impact", bg: "#dcfce7", fg: "#166534" },
  medium: { label: "Medium",      bg: "#fef9c3", fg: "#854d0e" },
  low:    { label: "Low",         bg: "#f3f4f6", fg: "#374151" },
};

const TAG_COLORS = {
  "Setup":       { bg: "#e6f1fb", fg: "#185FA5" },
  "Needs review":{ bg: "#faeeda", fg: "#854F0B" },
  "Lead signal": { bg: "#fbeaf0", fg: "#993556" },
  "Timing gap":  { bg: "#fff8e6", fg: "#7A5200" },
  "Repurpose":   { bg: "#eeedfe", fg: "#534AB7" },
};

function tagStyle(tag) {
  const t = TAG_COLORS[tag] || { bg: "#e6f5f2", fg: "#2a8c84" };
  return { background: t.bg, color: t.fg, padding: "3px 10px", borderRadius: 999,
           fontSize: 12, fontWeight: 600 };
}

function ImpactPill({ impact }) {
  const imp = IMPACT[impact] || IMPACT.medium;
  return (
    <span style={{ background: imp.bg, color: imp.fg, padding: "3px 10px",
                   borderRadius: 999, fontSize: 12, fontWeight: 700 }}>
      {imp.label}
    </span>
  );
}

export default function Opportunities({ goTab }) {
  const [data, setData]     = useState(null);
  const [err, setErr]       = useState("");
  const [loading, setLoading] = useState(true);

  const scan = () => {
    setLoading(true);
    setErr("");
    listOpportunities()
      .then(setData)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { scan(); }, []);

  const ops = data?.opportunities || [];

  return (
    <>
      {/* Agent header */}
      <div className="card aicard" style={{ marginBottom: 18 }}>
        <div className="row" style={{ alignItems: "flex-start", gap: 14 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 12, flexShrink: 0,
            background: "#eeedfe", color: "#534AB7",
            display: "grid", placeItems: "center", fontWeight: 800, fontSize: 16,
          }}>Op</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 16, color: "var(--ink)" }}>
              Opportunities agent
            </div>
            <div className="muted" style={{ fontSize: 13.5, marginTop: 3 }}>
              Watches your data — posts, leads, inbox, channels — and surfaces what to act on next. Free, instant, always up to date.
            </div>
          </div>
          <button className="btn-primary" onClick={scan} disabled={loading}
            style={{ flexShrink: 0, fontSize: 13, padding: "8px 16px" }}>
            {loading ? "Scanning…" : "Refresh"}
          </button>
        </div>

        {!loading && data && (
          <div className="row" style={{ marginTop: 16, gap: 20, paddingTop: 14, borderTop: "1px solid var(--line)" }}>
            {[
              { v: ops.filter(o => o.impact === "high").length,   l: "High impact" },
              { v: ops.filter(o => o.impact === "medium").length, l: "Medium" },
              { v: ops.length,                                    l: "Total found" },
            ].map(({ v, l }) => (
              <div key={l}>
                <div style={{ fontWeight: 800, fontSize: 22, color: "var(--teal-dark)" }}>{v}</div>
                <div className="muted" style={{ fontSize: 12 }}>{l}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {err && <div className="error" style={{ marginBottom: 12 }}>{err}</div>}

      {loading && !data && (
        <div className="empty">Scanning your data for opportunities…</div>
      )}

      {!loading && ops.length === 0 && (
        <div className="card" style={{ textAlign: "center", padding: "32px 24px" }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>✓</div>
          <div style={{ fontWeight: 700, fontSize: 16, color: "var(--ink)" }}>All caught up</div>
          <div className="muted" style={{ marginTop: 6, fontSize: 14 }}>
            Your AI team has nothing pressing to flag right now. Check back after your next post or campaign run.
          </div>
        </div>
      )}

      {ops.length > 0 && (
        <div className="pill-list">
          {ops.map((o) => (
            <div className="pill" key={o.id}
              style={{ flexDirection: "column", alignItems: "stretch", gap: 10 }}>
              <div className="row" style={{ alignItems: "center" }}>
                <span style={tagStyle(o.tag)}>{o.tag}</span>
                <div className="spacer" />
                <ImpactPill impact={o.impact} />
              </div>
              <div style={{ fontWeight: 700, fontSize: 15, color: "var(--ink)" }}>{o.title}</div>
              <div className="muted" style={{ fontSize: 13.5, lineHeight: 1.55 }}>{o.desc}</div>
              <div>
                <button className="btn-primary" style={{ fontSize: 13, padding: "8px 16px" }}
                  onClick={() => goTab(o.action_tab)}>
                  {o.action_label} →
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
