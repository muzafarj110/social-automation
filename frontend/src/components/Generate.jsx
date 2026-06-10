import { useEffect, useState } from "react";
import { generatePost, createPost } from "../api.js";

const POST_TYPES = [
  "Personal Story + Lesson",
  "Contrarian Take",
  "How-to / Tips",
  "Industry Insight",
  "Case Study",
];

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

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

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
