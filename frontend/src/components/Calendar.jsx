import { useEffect, useMemo, useState } from "react";
import { listPosts } from "../api.js";

const STATUS_CLASS = { published: "published", scheduled: "scheduled", draft: "draft", failed: "failed" };
const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const ymd = (d) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
function startOfWeek(d) {
  const x = new Date(d);
  const back = (x.getDay() + 6) % 7; // Monday-based
  x.setDate(x.getDate() - back);
  x.setHours(0, 0, 0, 0);
  return x;
}
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const sameDay = (a, b) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

// A real calendar: week or month grid, each day showing its posts as chips.
export default function Calendar() {
  const [posts, setPosts] = useState(null);
  const [err, setErr] = useState("");
  const [view, setView] = useState("week");
  const [anchor, setAnchor] = useState(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; });

  useEffect(() => { listPosts().then(setPosts).catch((e) => setErr(e.message)); }, []);

  const byDay = useMemo(() => {
    const m = {};
    (posts || []).forEach((p) => {
      const w = new Date(p.scheduled_for || p.created_at);
      (m[ymd(w)] ||= []).push({ ...p, when: w });
    });
    Object.values(m).forEach((list) => list.sort((a, b) => a.when - b.when));
    return m;
  }, [posts]);

  if (err) return <div className="error">{err}</div>;
  if (!posts) return <div className="empty">Loading…</div>;

  const today = new Date(); today.setHours(0, 0, 0, 0);

  let cells = [];
  let title = "";
  if (view === "week") {
    const start = startOfWeek(anchor);
    cells = Array.from({ length: 7 }, (_, i) => ({ date: addDays(start, i), dim: false }));
    const end = addDays(start, 6);
    title = `${start.toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${end.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`;
  } else {
    const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
    const gridStart = startOfWeek(first);
    cells = Array.from({ length: 42 }, (_, i) => {
      const date = addDays(gridStart, i);
      return { date, dim: date.getMonth() !== anchor.getMonth() };
    });
    title = first.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  }

  const move = (dir) => {
    if (view === "week") setAnchor(addDays(anchor, 7 * dir));
    else setAnchor(new Date(anchor.getFullYear(), anchor.getMonth() + dir, 1));
  };
  const goToday = () => { const d = new Date(); d.setHours(0, 0, 0, 0); setAnchor(d); };

  return (
    <div>
      <div className="cal-toolbar">
        <div className="seg">
          <button className={view === "week" ? "btn-primary" : "btn-secondary"} onClick={() => setView("week")}>Week</button>
          <button className={view === "month" ? "btn-primary" : "btn-secondary"} onClick={() => setView("month")}>Month</button>
        </div>
        <button className="btn-secondary" onClick={() => move(-1)} aria-label="Previous">←</button>
        <button className="btn-secondary" onClick={goToday}>Today</button>
        <button className="btn-secondary" onClick={() => move(1)} aria-label="Next">→</button>
        <div className="cal-title" style={{ marginLeft: "auto" }}>{title}</div>
      </div>

      <div className="cal-grid" style={{ marginBottom: 8 }}>
        {DOW.map((d) => <div className="cal-dow" key={d}>{d}</div>)}
      </div>
      <div className="cal-grid">
        {cells.map(({ date, dim }, i) => {
          const items = byDay[ymd(date)] || [];
          return (
            <div className={`cal-cell${dim ? " dim" : ""}${sameDay(date, today) ? " today" : ""}`} key={i}>
              <div className="cal-daynum">{date.getDate()}</div>
              {items.slice(0, 4).map((p) => (
                <div className={`cal-chip chip-${STATUS_CLASS[p.status] || "draft"}`} key={p.id} title={p.body}>
                  <span className="t">{p.scheduled_for ? p.when.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "•"} </span>
                  {(p.body || "").slice(0, 30)}
                </div>
              ))}
              {items.length > 4 && <div className="muted" style={{ fontSize: 11 }}>+{items.length - 4} more</div>}
            </div>
          );
        })}
      </div>

      {posts.length === 0 && (
        <div className="empty" style={{ marginTop: 16 }}>
          Nothing on the calendar yet. Create a campaign or a quick post to fill it.
        </div>
      )}
    </div>
  );
}
