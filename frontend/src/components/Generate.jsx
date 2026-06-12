import { useEffect, useState } from "react";
import {
  generatePost,
  createPost,
  qaCheck,
  optimizeContent,
  generateInfographic,
} from "../api.js";

const POST_TYPES = [
  "Personal Story + Lesson",
  "Contrarian Take",
  "How-to / Tips",
  "Industry Insight",
  "Case Study",
];

// Render a free-form Hub result object as readable key → value blocks.
function HubBlocks({ data }) {
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
          {typeof v === "string" ? (
            <p style={{ margin: "2px 0", lineHeight: 1.5, fontSize: 13 }}>{v}</p>
          ) : Array.isArray(v) ? (
            <ul style={{ margin: "2px 0", paddingLeft: 18, fontSize: 13 }}>
              {v.map((x, i) => <li key={i}>{typeof x === "string" ? x : JSON.stringify(x)}</li>)}
            </ul>
          ) : (
            <span style={{ fontSize: 13 }}>{String(v)}</span>
          )}
        </div>
      ))}
    </div>
  );
}

function pickOptimized(data) {
  for (const k of ["optimized_content", "optimized", "improved_content", "improved",
                   "rewritten", "rewrite", "content", "full_post", "result"]) {
    if (typeof data?.[k] === "string" && data[k].trim()) return data[k].trim();
  }
  return null;
}

export default function Generate({ accounts, onSaved, goConnect }) {
  const [form, setForm] = useState({
    topic: "",
    post_type: POST_TYPES[0],
    audience: "early-stage founders",
    tone: "professional but human",
    include_cta: "question to comments",
  });
  const [accountId, setAccountId] = useState(accounts[0]?.id || "");
  // Accounts load async after this component mounts — pick a default once they arrive.
  useEffect(() => {
    if (!accountId && accounts.length) setAccountId(accounts[0].id);
  }, [accounts]); // eslint-disable-line
  const [result, setResult] = useState(null);
  const [body, setBody] = useState("");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [qa, setQa] = useState(null);
  const [info, setInfo] = useState(null);
  const [task, setTask] = useState(""); // which sub-action is running

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const runQa = async () => {
    setError(""); setTask("qa"); setQa(null);
    try {
      const res = await qaCheck({ content: body, topic: form.topic, audience: form.audience });
      setQa(res);
    } catch (e) { setError(e.message); }
    finally { setTask(""); }
  };

  const improve = async () => {
    setError(""); setTask("improve");
    try {
      const res = await optimizeContent({ content: body, goal: "engagement", tone: form.tone });
      const better = pickOptimized(res.data);
      if (better) { setBody(better); setMsg("Post improved by AI. Re-run the quality check to compare."); setQa(null); }
      else setMsg("Optimizer ran but returned no rewrite.");
    } catch (e) { setError(e.message); }
    finally { setTask(""); }
  };

  const makeInfographic = async () => {
    setError(""); setTask("info"); setInfo(null);
    try {
      const res = await generateInfographic({ topic: form.topic, content_points: body });
      setInfo(res.data);
    } catch (e) { setError(e.message); }
    finally { setTask(""); }
  };

  const doGenerate = async (e) => {
    e.preventDefault();
    setError("");
    setMsg("");
    setBusy(true);
    try {
      const res = await generatePost(form);
      const data = res.data || {};
      setResult(data);
      setBody(data.full_post || "");
      setQa(null);
      setInfo(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const saveDraft = async () => {
    setError("");
    setMsg("");
    if (!accountId) {
      setError("Select a LinkedIn account first.");
      return;
    }
    setBusy(true);
    try {
      await createPost({
        account_id: Number(accountId),
        body,
        hashtags: result?.hashtags || null,
      });
      setMsg("Saved as draft. Find it under Posts to publish or schedule.");
      onSaved?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {error && <div className="error">{error}</div>}
      {msg && <div className="success">{msg}</div>}

      <div className="card">
        <h2>Generate a LinkedIn post</h2>
        <form onSubmit={doGenerate}>
          <label>Topic</label>
          <textarea
            style={{ minHeight: 70 }}
            value={form.topic}
            onChange={set("topic")}
            placeholder="What's the post about?"
            required
          />
          <div className="row">
            <div style={{ flex: 1, minWidth: 200 }}>
              <label>Post type</label>
              <select value={form.post_type} onChange={set("post_type")}>
                {POST_TYPES.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <label>Audience</label>
              <input value={form.audience} onChange={set("audience")} />
            </div>
          </div>
          <div className="row">
            <div style={{ flex: 1, minWidth: 200 }}>
              <label>Tone</label>
              <input value={form.tone} onChange={set("tone")} />
            </div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <label>Call to action</label>
              <input value={form.include_cta} onChange={set("include_cta")} />
            </div>
          </div>
          <div className="row" style={{ marginTop: 14 }}>
            <button className="btn-primary" disabled={busy || !form.topic.trim()}>
              {busy ? "Generating…" : "Generate"}
            </button>
          </div>
        </form>
      </div>

      {result && (
        <div className="card">
          <h2>Review & save</h2>
          {result.why_this_works && <p className="muted">Why this works: {result.why_this_works}</p>}
          <label>Post body (editable)</label>
          <textarea value={body} onChange={(e) => setBody(e.target.value)} />
          {result.hashtags?.length > 0 && (
            <div className="hashtags">{result.hashtags.join("  ")}</div>
          )}
          {result.best_time_to_post && (
            <p className="muted" style={{ marginTop: 8 }}>
              Suggested time: {result.best_time_to_post}
            </p>
          )}

          <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid #e8ecf7" }}>
            <div className="row">
              <strong style={{ color: "var(--blue)" }}>Quality check</strong>
              <span className="muted" style={{ fontSize: 12 }}>
                We score the post, review it, and flag robotic phrasing before you post — not blind AI output.
              </span>
            </div>
            <div className="row" style={{ marginTop: 8 }}>
              <button className="btn-secondary" disabled={!!task || !body.trim()} onClick={runQa}>
                {task === "qa" ? "Checking…" : "Run quality check"}
              </button>
              <button className="btn-secondary" disabled={!!task || !body.trim()} onClick={improve}>
                {task === "improve" ? "Improving…" : "Improve with AI"}
              </button>
            </div>
            {qa && (
              <div className="row" style={{ marginTop: 12, gap: 12, alignItems: "stretch" }}>
                <div className="card" style={{ flex: 1, margin: 0 }}>
                  <h3>Score</h3><HubBlocks data={qa.score} />
                </div>
                <div className="card" style={{ flex: 1, margin: 0 }}>
                  <h3>QA review</h3><HubBlocks data={qa.qa} />
                </div>
                <div className="card" style={{ flex: 1, margin: 0 }}>
                  <h3>AI-detection</h3><HubBlocks data={qa.ai_detection} />
                </div>
              </div>
            )}
          </div>

          <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid #e8ecf7" }}>
            <div className="row">
              <strong style={{ color: "var(--blue)" }}>Infographic</strong>
              <span className="muted" style={{ fontSize: 12 }}>Optional — turn this post into an infographic concept.</span>
              <div className="spacer" />
              <button className="btn-secondary" disabled={!!task || !body.trim()} onClick={makeInfographic}>
                {task === "info" ? "Generating…" : "Generate infographic"}
              </button>
            </div>
            {info && <div style={{ marginTop: 10 }}><HubBlocks data={info} /></div>}
          </div>

          <label style={{ marginTop: 14 }}>Post to account</label>
          {accounts.length === 0 ? (
            <p className="muted">
              No linked accounts.{" "}
              <a style={{ color: "var(--teal)", cursor: "pointer" }} onClick={goConnect}>
                Connect one →
              </a>
            </p>
          ) : (
            <select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.display_name || a.zernio_account_id}
                </option>
              ))}
            </select>
          )}

          <div className="row" style={{ marginTop: 14 }}>
            <button className="btn-primary" disabled={busy || !body.trim()} onClick={saveDraft}>
              Save as draft
            </button>
          </div>
        </div>
      )}
    </>
  );
}
