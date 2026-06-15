import { useEffect, useState } from "react";
import { teamRun, listTeamRuns, getTeamRun, approveTeamRun, deletePost } from "../api.js";

const AGENTS = ["Strategist", "Packager", "Writer", "Producer", "Publisher"];
const PLATFORM_LABEL = { linkedin: "LinkedIn", twitter: "X", instagram: "Instagram", facebook: "Facebook" };

function Pipeline({ active }) {
  // active = index currently working (-1 = done/idle)
  return (
    <div className="row" style={{ gap: 6, flexWrap: "wrap", marginTop: 6 }}>
      {AGENTS.map((a, i) => {
        const done = active === -1 || i < active;
        const now = i === active;
        return (
          <span key={a} className={`badge ${now ? "pending" : done ? "published" : "draft"}`}>
            {done ? "✓ " : now ? "● " : ""}{a}
          </span>
        );
      })}
    </div>
  );
}

function qaClass(s) { return s >= 85 ? "published" : s >= 70 ? "pending" : "draft"; }

export default function ContentTeam({ goTab }) {
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [approving, setApproving] = useState(false);
  const [count, setCount] = useState(3);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const loadLatestDraft = async () => {
    try {
      const runs = await listTeamRuns();
      const draft = (runs || []).find((r) => r.status === "draft");
      if (draft) {
        const full = await getTeamRun(draft.id);
        if ((full.posts || []).length > 0) setRun(full);   // ignore empty/orphan runs
      }
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { loadLatestDraft(); }, []); // eslint-disable-line

  const doRun = async () => {
    setError(""); setInfo(""); setRunning(true); setRun(null);
    try { setRun(await teamRun(count)); }
    catch (e) { setError(e.message); }
    finally { setRunning(false); }
  };

  const doApprove = async () => {
    setError(""); setInfo(""); setApproving(true);
    try {
      const r = await approveTeamRun(run.id);
      setRun(r);
      setInfo(`Scheduled ${r.scheduled} post${r.scheduled === 1 ? "" : "s"} across the coming days.`
        + (r.errors?.length ? ` (${r.errors.length} couldn't be scheduled.)` : ""));
    } catch (e) { setError(e.message); }
    finally { setApproving(false); }
  };

  const skip = async (postId) => {
    setError("");
    try { await deletePost(postId); setRun(await getTeamRun(run.id)); }
    catch (e) { setError(e.message); }
  };

  if (loading) return <div className="empty">Loading your content team…</div>;

  const drafts = (run?.posts || []).filter((p) => p.status === "draft");
  const isScheduled = run?.status === "scheduled";

  return (
    <>
      {error && <div className="flash error">{error}</div>}
      {info && <div className="flash success">{info}</div>}

      <div className="card aicard">
        <div className="row" style={{ alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0 }}>Your content team</h2>
            <p className="muted" style={{ margin: "4px 0 0" }}>
              A strategist, writer and producer draft a week of on-brand content. You approve once — it schedules and learns from results.
            </p>
          </div>
          <div className="spacer" />
          {!running && (
            <div className="row" style={{ gap: 8 }}>
              <select value={count} onChange={(e) => setCount(Number(e.target.value))} style={{ width: 130 }}>
                {[3, 5, 7].map((n) => <option key={n} value={n}>{n} posts</option>)}
              </select>
              <button className="btn-primary" onClick={doRun}>{run ? "Run again" : "Run my team"}</button>
            </div>
          )}
        </div>
        <Pipeline active={running ? 4 : -1} />
      </div>

      {running && (
        <div className="card"><div className="studio-loading"><span className="spinner" />Your team is drafting this week's content… this can take a minute.</div></div>
      )}

      {run && !running && (
        <>
          {run.brief && (
            <div className="card">
              <h3 style={{ marginBottom: 6 }}>This week's brief</h3>
              <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.6 }}>{run.brief}</p>
            </div>
          )}

          {isScheduled ? (
            <div className="card">
              <h2>Scheduled ✓</h2>
              <p className="muted" style={{ marginTop: -6 }}>Your team queued this batch. Track it on the Calendar or Posts.</p>
              <div className="row" style={{ marginTop: 10 }}>
                <button className="btn-secondary" onClick={() => goTab("calendar")}>Open Calendar</button>
                <button className="btn-secondary" onClick={() => goTab("posts")}>Open Posts</button>
              </div>
            </div>
          ) : drafts.length === 0 ? (
            <div className="empty">No drafts in this run. Run your team to generate a fresh batch.</div>
          ) : (
            <>
              <div className="row" style={{ alignItems: "center", marginBottom: 4 }}>
                <h2 style={{ margin: 0 }}>Review & approve — {drafts.length} post{drafts.length === 1 ? "" : "s"}</h2>
              </div>
              {drafts.map((p) => (
                <div className="card" key={p.id}>
                  <div className="row" style={{ alignItems: "center", marginBottom: 6 }}>
                    <span className="badge kind">{PLATFORM_LABEL[p.platform] || p.platform}</span>
                    {p.qa_score != null && <span className={`badge ${qaClass(p.qa_score)}`}>QA {p.qa_score}</span>}
                    <div className="spacer" />
                    <button className="btn-ghost" style={{ fontSize: 12, padding: "4px 10px" }} onClick={() => goTab("posts")}>Edit in Posts</button>
                    <button className="btn-danger" style={{ fontSize: 12, padding: "4px 10px" }} onClick={() => skip(p.id)}>Skip</button>
                  </div>
                  <div className="post-body">{p.body}</div>
                  {p.hashtags?.length > 0 && (
                    <div className="hashtags">{p.hashtags.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" ")}</div>
                  )}
                </div>
              ))}
              <div className="card" style={{ position: "sticky", bottom: 0 }}>
                <div className="row" style={{ alignItems: "center" }}>
                  <button className="btn-primary" disabled={approving} onClick={doApprove}>
                    {approving ? "Scheduling…" : `Approve & schedule all (${drafts.length})`}
                  </button>
                  <span className="muted" style={{ fontSize: 13 }}>Posts go out one per day, starting tomorrow at 9:00.</span>
                </div>
              </div>
            </>
          )}
        </>
      )}

      {!run && !running && (
        <div className="empty">Pick how many posts and hit "Run my team" — your team drafts the batch for you to approve.</div>
      )}
    </>
  );
}
