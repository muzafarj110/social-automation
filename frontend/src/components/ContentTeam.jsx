import { useEffect, useState } from "react";
import { teamPlan, teamRun, listTeamRuns, getTeamRun, approveTeamRun, deletePost } from "../api.js";

const AGENTS = ["Strategist", "Packager", "Writer", "Producer", "Publisher"];
const PLATFORM_LABEL = { linkedin: "LinkedIn", twitter: "X", instagram: "Instagram", facebook: "Facebook" };
const qaClass = (s) => (s >= 85 ? "published" : s >= 70 ? "pending" : "draft");

function Pipeline({ active }) {
  return (
    <div className="row" style={{ gap: 6, flexWrap: "wrap", marginTop: 6 }}>
      {AGENTS.map((a, i) => {
        const done = active === -1 || i < active;
        const now = i === active;
        return <span key={a} className={`badge ${now ? "pending" : done ? "published" : "draft"}`}>{done ? "✓ " : now ? "● " : ""}{a}</span>;
      })}
    </div>
  );
}

export default function ContentTeam({ goTab }) {
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [planning, setPlanning] = useState(false);
  const [running, setRunning] = useState(false);
  const [approving, setApproving] = useState(false);
  const [count, setCount] = useState(3);
  const [brief, setBrief] = useState("");
  const [topics, setTopics] = useState(null); // null = no plan yet; array = plan editor
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const runs = await listTeamRuns();
        const draft = (runs || []).find((r) => r.status === "draft");
        if (draft) {
          const full = await getTeamRun(draft.id);
          if ((full.posts || []).length > 0) setRun(full);
        }
      } catch (e) { setError(e.message); }
      finally { setLoading(false); }
    })();
  }, []);

  const doPlan = async () => {
    setError(""); setInfo(""); setPlanning(true); setRun(null);
    try {
      const p = await teamPlan(count);
      setBrief(p.brief || "");
      setTopics(p.topics || []);
    } catch (e) { setError(e.message); }
    finally { setPlanning(false); }
  };

  const doGenerate = async () => {
    const clean = (topics || []).map((t) => t.trim()).filter(Boolean);
    if (clean.length === 0) { setError("Add at least one topic."); return; }
    setError(""); setInfo(""); setRunning(true);
    try {
      const r = await teamRun({ brief, topics: clean });
      setRun(r); setTopics(null);
    } catch (e) { setError(e.message); }
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

  const startOver = () => { setRun(null); setTopics(null); setBrief(""); setInfo(""); setError(""); };
  const setTopicAt = (i, v) => setTopics(topics.map((t, j) => (j === i ? v : t)));
  const removeTopic = (i) => setTopics(topics.filter((_, j) => j !== i));

  if (loading) return <div className="empty">Loading your content team…</div>;

  const drafts = (run?.posts || []).filter((p) => p.status === "draft");
  const isScheduled = run?.status === "scheduled";
  const busy = planning || running;
  const pipeActive = planning ? 0 : running ? 3 : -1;

  return (
    <>
      {error && <div className="flash error">{error}</div>}
      {info && <div className="flash success">{info}</div>}

      <div className="card aicard">
        <div className="row" style={{ alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0 }}>Your content team</h2>
            <p className="muted" style={{ margin: "4px 0 0" }}>
              The strategist plans your week (and learns from results). You tweak it, the team writes, you approve once.
            </p>
          </div>
          <div className="spacer" />
          {!busy && !run && topics === null && (
            <div className="row" style={{ gap: 8 }}>
              <select value={count} onChange={(e) => setCount(Number(e.target.value))} style={{ width: 120 }}>
                {[3, 5, 7].map((n) => <option key={n} value={n}>{n} posts</option>)}
              </select>
              <button className="btn-primary" onClick={doPlan}>Plan my week</button>
            </div>
          )}
          {!busy && (run || topics !== null) && (
            <button className="btn-secondary" onClick={startOver}>Start new plan</button>
          )}
        </div>
        <Pipeline active={pipeActive} />
      </div>

      {planning && <div className="card"><div className="studio-loading"><span className="spinner" />Your strategist is planning the week…</div></div>}
      {running && <div className="card"><div className="studio-loading"><span className="spinner" />Your team is writing & quality-checking the batch…</div></div>}

      {/* Plan editor */}
      {!busy && topics !== null && !run && (
        <div className="card">
          <h2>Review the plan</h2>
          <p className="muted" style={{ marginTop: -6 }}>Edit the brief and topics — the team writes one post per topic.</p>
          <label>This week's brief</label>
          <textarea value={brief} onChange={(e) => setBrief(e.target.value)} style={{ minHeight: 90 }} />
          <label style={{ marginTop: 12 }}>Topics ({topics.length})</label>
          <div className="pill-list" style={{ marginTop: 6 }}>
            {topics.map((t, i) => (
              <div className="row" key={i} style={{ gap: 8 }}>
                <input value={t} onChange={(e) => setTopicAt(i, e.target.value)} style={{ flex: 1 }} placeholder={`Topic ${i + 1}`} />
                <button className="btn-ghost" onClick={() => removeTopic(i)} title="Remove">✕</button>
              </div>
            ))}
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn-primary" onClick={doGenerate}>Generate {topics.filter((t) => t.trim()).length} posts →</button>
            <button className="btn-secondary" onClick={() => setTopics([...topics, ""])}>+ Add topic</button>
            <button className="btn-ghost" onClick={doPlan}>↻ Regenerate plan</button>
          </div>
        </div>
      )}

      {/* Generated batch */}
      {run && !busy && (
        <>
          {run.brief && (
            <div className="card">
              <h3 style={{ marginBottom: 6 }}>This week's brief</h3>
              <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{run.brief}</p>
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
            <div className="empty">No drafts left in this run. Start a new plan to generate a fresh batch.</div>
          ) : (
            <>
              <h2 style={{ margin: "0 0 4px" }}>Review & approve — {drafts.length} post{drafts.length === 1 ? "" : "s"}</h2>
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
              <div className="card">
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

      {!busy && topics === null && !run && (
        <div className="empty">Pick how many posts and hit "Plan my week" — your strategist drafts a plan for you to tweak.</div>
      )}
    </>
  );
}
