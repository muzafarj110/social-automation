import { useEffect, useState } from "react";
import {
  generatePost,
  createPost,
  qaCheck,
  optimizeContent,
  generateInfographic,
} from "../api.js";
import HubBlocks from "./HubResult.jsx";

const POST_TYPES = [
  "Personal Story + Lesson",
  "Contrarian Take",
  "How-to / Tips",
  "Industry Insight",
  "Case Study",
];

function pickOptimized(data) {
  for (const k of ["optimized_content", "optimized", "improved_content", "improved",
                   "rewritten", "rewrite", "content", "full_post", "result"]) {
    if (typeof data?.[k] === "string" && data[k].trim()) return data[k].trim();
  }
  return null;
}

// The Hub returns infographics as a self-contained HTML document — preview it
// live in a sandboxed iframe and let the user download it.
function InfographicResult({ data }) {
  if (!data) return null;
  const download = () => {
    const blob = new Blob([data.html || ""], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = data.download_filename || "infographic.html";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };
  return (
    <div>
      <div className="row" style={{ marginBottom: 8, alignItems: "center" }}>
        <div>
          <strong style={{ color: "var(--blue)" }}>{data.title || "Infographic"}</strong>
          {data.type && <span className="muted" style={{ marginLeft: 8, fontSize: 12 }}>{data.type}</span>}
        </div>
        <div className="spacer" />
        {Array.isArray(data.color_palette) && (
          <div className="row" style={{ gap: 4 }}>
            {data.color_palette.map((c, i) => (
              <span key={i} title={c} style={{
                width: 18, height: 18, borderRadius: 4, background: c,
                display: "inline-block", border: "1px solid #ddd",
              }} />
            ))}
          </div>
        )}
        {data.html && (
          <button className="btn-secondary" onClick={download} style={{ marginLeft: 8 }}>
            Download HTML
          </button>
        )}
      </div>
      {data.summary && <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>{data.summary}</p>}
      {data.html ? (
        <iframe
          title="Infographic preview"
          srcDoc={data.html}
          sandbox=""
          style={{
            width: "100%", height: 560, border: "1px solid #e8ecf7",
            borderRadius: "var(--radius)", background: "#fff",
          }}
        />
      ) : (
        <HubBlocks data={data} />
      )}
    </div>
  );
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
  const [qaNote, setQaNote] = useState("");
  const [showQaDetail, setShowQaDetail] = useState(false);
  const [info, setInfo] = useState(null);
  const [task, setTask] = useState(""); // which sub-action is running

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  // Check quality and, if the score is below par, let the AI polish it
  // automatically — then re-check. The user only reviews if they want to.
  const runQa = async () => {
    setError(""); setTask("qa"); setQa(null); setQaNote(""); setShowQaDetail(false);
    try {
      let res = await qaCheck({ content: body, topic: form.topic, audience: form.audience });
      const score0 = res?.score?.overall_score;
      if (typeof score0 === "number" && score0 < 75) {
        setTask("improve");
        const opt = await optimizeContent({ content: body, goal: "engagement", tone: form.tone });
        const better = pickOptimized(opt.data);
        if (better && better !== body) {
          setBody(better);
          const res2 = await qaCheck({ content: better, topic: form.topic, audience: form.audience });
          setQaNote(`Below par (${score0}/100), so the AI polished it automatically — now ${res2?.score?.overall_score ?? "?"}/100.`);
          res = res2;
        }
      }
      setQa(res);
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
      setQaNote("");
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
        infographic_html: info?.html || null,
      });
      setMsg(info?.html
        ? "Saved as draft with its infographic. Find it under Posts to publish or schedule."
        : "Saved as draft. Find it under Posts to publish or schedule.");
      onSaved?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {error && <div className="flash error" role="alert">{error}</div>}
      {msg && <div className="flash success" role="status">{msg}</div>}

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
            <div className="hashtags">
              {result.hashtags.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" ")}
            </div>
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
                We score it, and if it's below par the AI polishes it automatically — no manual review unless you want it.
              </span>
            </div>
            <div className="row" style={{ marginTop: 8 }}>
              <button className="btn-secondary" disabled={!!task || !body.trim()} onClick={runQa}>
                {task === "qa" ? "Checking…" : task === "improve" ? "Polishing…" : "Check & polish"}
              </button>
            </div>
            {qa && (() => {
              const s = qa.score || {};
              const a = qa.ai_detection || {};
              const score = s.overall_score;
              const good = typeof score !== "number" || score >= 75;
              return (
                <div style={{ marginTop: 12 }}>
                  <div className="row" style={{ gap: 10, alignItems: "center" }}>
                    <span className="badge" style={{ background: good ? "#dcfce7" : "#fef9c3", color: good ? "#166534" : "#854d0e" }}>
                      {typeof score === "number" ? `Score ${score}` : "Checked"}{s.verdict ? ` · ${s.verdict}` : ""}
                    </span>
                    {a.verdict && <span className="muted" style={{ fontSize: 12 }}>AI-detection: {a.verdict}</span>}
                    <div className="spacer" />
                    <a style={{ cursor: "pointer", fontSize: 12, fontWeight: 600, color: "var(--teal)" }}
                       onClick={() => setShowQaDetail((v) => !v)}>
                      {showQaDetail ? "Hide detailed review" : "View detailed review"}
                    </a>
                  </div>
                  {qaNote
                    ? <div className="success" style={{ marginTop: 8 }}>{qaNote}</div>
                    : good && <div className="muted" style={{ marginTop: 6, fontSize: 13 }}>✓ Good to post — the AI didn't find changes worth making.</div>}
                  {showQaDetail && (
                    <div className="row" style={{ marginTop: 12, gap: 12, alignItems: "stretch" }}>
                      <div className="card" style={{ flex: 1, margin: 0 }}><h3>Score</h3><HubBlocks data={qa.score} /></div>
                      <div className="card" style={{ flex: 1, margin: 0 }}><h3>QA review</h3><HubBlocks data={qa.qa} /></div>
                      <div className="card" style={{ flex: 1, margin: 0 }}><h3>AI-detection</h3><HubBlocks data={qa.ai_detection} /></div>
                    </div>
                  )}
                </div>
              );
            })()}
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
            {info && <div style={{ marginTop: 10 }}><InfographicResult data={info} /></div>}
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
