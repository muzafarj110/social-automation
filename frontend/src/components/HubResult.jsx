// Generic renderer for arbitrary Hub model JSON — turns a plain result object
// into readable key -> value blocks. Shared by Generate.jsx and
// ProfileStudio.jsx (previously duplicated verbatim in both).

function objText(o) {
  return Object.entries(o)
    .filter(([k]) => !k.startsWith("_"))
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v && typeof v === "object" ? JSON.stringify(v) : v}`)
    .join(" — ");
}

function renderVal(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === "string") return <p style={{ margin: "2px 0", lineHeight: 1.5, fontSize: 13 }}>{v}</p>;
  if (typeof v === "number" || typeof v === "boolean") return <span style={{ fontSize: 13 }}>{String(v)}</span>;
  if (Array.isArray(v))
    return (
      <ul style={{ margin: "2px 0", paddingLeft: 18, fontSize: 13 }}>
        {v.map((x, i) => <li key={i} style={{ marginBottom: 4 }}>{x && typeof x === "object" ? objText(x) : String(x)}</li>)}
      </ul>
    );
  if (typeof v === "object")
    return (
      <div>
        {Object.entries(v).filter(([k]) => !k.startsWith("_")).map(([k, vv]) => (
          <div key={k} style={{ fontSize: 13, marginBottom: 2 }}>
            <span style={{ fontWeight: 600, color: "var(--mid)" }}>{k.replace(/_/g, " ")}: </span>
            {vv && typeof vv === "object" ? objText(vv) : String(vv)}
          </div>
        ))}
      </div>
    );
  return <span>{String(v)}</span>;
}

export default function HubBlocks({ data }) {
  if (!data) return null;
  const entries = Object.entries(data).filter(([k]) => !k.startsWith("_"));
  if (!entries.length) return <div className="muted">No details.</div>;
  return (
    <div>
      {entries.map(([k, v]) => (
        <div key={k} style={{ marginBottom: 8 }}>
          <div style={{ fontWeight: 600, color: "var(--mid)", textTransform: "capitalize", fontSize: 13 }}>
            {k.replace(/_/g, " ")}
          </div>
          {renderVal(v)}
        </div>
      ))}
    </div>
  );
}
