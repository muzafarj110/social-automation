// Checks whether a brand profile has enough set to guide AI generation.
// Reused wherever content gets generated so the same rule applies everywhere.
export function isBrandReady(brand) {
  return !!(brand && (brand.voice || brand.brand_name));
}

// Persistent (not dismissible) amber notice shown wherever generation would
// fall back to generic defaults — matches the amber warning style already
// used for the paused-automation banner in Accounts.jsx. Purely informational:
// generation is never blocked, just made visible when it's using placeholders.
export default function BrandWarning({ goTab }) {
  return (
    <div className="card" style={{ borderLeft: "4px solid #d97706", marginBottom: 16 }}>
      <div className="row" style={{ alignItems: "center" }}>
        <div>
          <div style={{ fontWeight: 600, color: "var(--ink)" }}>Using generic defaults</div>
          <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>
            No brand profile set yet, so content uses placeholder audience ("professionals") and tone
            ("professional but human") instead of your own voice.
          </p>
        </div>
        <div className="spacer" />
        <button className="btn-secondary" onClick={() => goTab("strategy")}>Set up brand</button>
      </div>
    </div>
  );
}
