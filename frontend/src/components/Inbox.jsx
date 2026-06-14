import { useEffect, useState } from "react";
import {
  generateApproval,
  listInbox,
  editApproval,
  approveApproval,
  rejectApproval,
} from "../api.js";

const KINDS = [
  ["comment", "Comment"],
  ["dm", "DM"],
  ["outreach", "Outreach"],
  ["profile", "Profile"],
];

// Hub request params per kind — field names match the Hub's OpenAPI schema and
// are passed straight through. `req` marks fields the Hub requires.
const PARAM_FIELDS = {
  comment: [
    { name: "post_topic", label: "Post topic", placeholder: "what the post you're replying to is about", req: true },
    { name: "post_summary", label: "Post summary", placeholder: "a sentence or two about the post" },
    { name: "your_role", label: "Your role", placeholder: "Founder @ Acme", req: true },
    { name: "your_goal", label: "Your goal", placeholder: "build visibility" },
    { name: "tone", label: "Tone", placeholder: "professional" },
  ],
  dm: [
    { name: "prospect_name", label: "Prospect name", placeholder: "Jane Doe", req: true },
    { name: "prospect_role", label: "Prospect role", placeholder: "VP Eng @ Globex", req: true },
    { name: "your_role", label: "Your role", placeholder: "Founder @ Acme", req: true },
    { name: "your_offer", label: "Your offer", placeholder: "AI onboarding tool" },
    { name: "goal", label: "Goal", placeholder: "book a discovery call" },
    { name: "num_messages", label: "Number of messages", placeholder: "3", type: "number" },
  ],
  outreach: [
    { name: "your_role", label: "Your role", placeholder: "Founder @ Acme", req: true },
    { name: "your_offer", label: "Your offer", placeholder: "AI onboarding tool", req: true },
    { name: "target_role", label: "Target role", placeholder: "VP Engineering", req: true },
    { name: "target_industry", label: "Target industry", placeholder: "B2B SaaS" },
    { name: "campaign_goal", label: "Campaign goal", placeholder: "book discovery calls" },
    { name: "num_touchpoints", label: "Touchpoints", placeholder: "4", type: "number" },
  ],
  profile: [
    { name: "current_headline", label: "Current headline", placeholder: "Founder @ Acme", req: true },
    { name: "current_summary", label: "Current summary / about", placeholder: "your existing about section", req: true },
    { name: "role", label: "Role", placeholder: "Founder", req: true },
    { name: "industry", label: "Industry", placeholder: "B2B SaaS", req: true },
    { name: "goals", label: "Goals", placeholder: "attract clients and opportunities" },
  ],
};

const NUMERIC = new Set(["num_messages", "num_touchpoints"]);

function InboxCard({ item, onChange }) {
  const [text, setText] = useState(item.draft_text || "");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const pending = item.status === "pending";
  const willAutoSend = item.kind === "comment" && item.context?.comment_id;

  const run = (fn) => async () => {
    setError("");
    setMsg("");
    setBusy(true);
    try {
      await fn();
      onChange();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const saveEdit = run(async () => {
    if (text.trim() !== (item.draft_text || "").trim()) {
      await editApproval(item.id, text);
    }
  });

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setMsg("Copied to clipboard.");
    } catch {
      setMsg("Copy failed — select and copy manually.");
    }
  };

  return (
    <div className="card">
      <div className="row">
        <span className="badge kind">{item.kind}</span>
        <span className={`badge ${item.status}`}>{item.status}</span>
        {item.executed_via && <span className="muted">via {item.executed_via}</span>}
        <div className="spacer" />
        {item.context?.post_url && (
          <a href={item.context.post_url} target="_blank" rel="noreferrer"
             style={{ color: "var(--teal)", fontSize: 13, fontWeight: 600 }}>
            Target ↗
          </a>
        )}
      </div>

      {pending ? (
        <textarea value={text} onChange={(e) => setText(e.target.value)} style={{ marginTop: 10 }} />
      ) : (
        <div className="post-body">{item.draft_text}</div>
      )}

      {item.error && <div className="error">{item.error}</div>}
      {error && <div className="error">{error}</div>}
      {msg && <div className="success">{msg}</div>}

      {pending && (
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn-primary" disabled={busy} onClick={run(async () => {
            if (text.trim() !== (item.draft_text || "").trim()) await editApproval(item.id, text);
            await approveApproval(item.id);
          })}>
            {willAutoSend ? "Approve & post reply" : "Approve (ready to send)"}
          </button>
          <button className="btn-secondary" disabled={busy} onClick={saveEdit}>
            Save edit
          </button>
          <div className="spacer" />
          <button className="btn-danger" disabled={busy} onClick={run(() => rejectApproval(item.id))}>
            Reject
          </button>
        </div>
      )}

      {item.status === "approved" && (
        <div className="row" style={{ marginTop: 12 }}>
          <span className="muted">No official API for this action — send it manually on LinkedIn.</span>
          <div className="spacer" />
          <button className="btn-secondary" onClick={copy}>Copy text</button>
        </div>
      )}
    </div>
  );
}

export default function Inbox({ accounts, refreshKey }) {
  const [kind, setKind] = useState("comment");
  const [accountId, setAccountId] = useState("");
  const [params, setParams] = useState({});
  const [commentId, setCommentId] = useState("");
  const [postUrl, setPostUrl] = useState("");
  const [autoSend, setAutoSend] = useState(false);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setError("");
    try {
      setItems(await listInbox(statusFilter));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [statusFilter, refreshKey]); // eslint-disable-line

  const fields = PARAM_FIELDS[kind] || [];
  const setParam = (name) => (e) => setParams({ ...params, [name]: e.target.value });

  const doGenerate = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const cleanParams = Object.fromEntries(
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== null && String(v).trim())
          .map(([k, v]) => [k, NUMERIC.has(k) ? Number(v) : v])
      );
      const context = {};
      if (kind === "comment" && postUrl.trim()) context.post_url = postUrl.trim();
      if (kind === "comment" && commentId.trim()) context.comment_id = commentId.trim();
      await generateApproval({
        kind,
        account_id: accountId ? Number(accountId) : null,
        params: cleanParams,
        context: Object.keys(context).length ? context : null,
        auto_send: kind === "comment" && commentId.trim() ? autoSend : false,
      });
      setParams({});
      setCommentId("");
      setPostUrl("");
      setAutoSend(false);
      if (statusFilter !== "pending") setStatusFilter("pending");
      else load();
    } catch (e2) {
      setError(e2.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="card">
        <h2>Draft an action</h2>
        <form onSubmit={doGenerate}>
          <div className="row">
            {KINDS.map(([id, label]) => (
              <button
                type="button"
                key={id}
                className={kind === id ? "btn-primary" : "btn-secondary"}
                onClick={() => { setKind(id); setParams({}); }}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="grid-2">
            {fields.map((f) => (
              <div key={f.name}>
                <label>
                  {f.label}{" "}
                  {f.req ? <span style={{ color: "var(--teal)" }}>*</span>
                         : <span className="muted">(optional)</span>}
                </label>
                <input
                  type={f.type || "text"}
                  value={params[f.name] ?? ""}
                  placeholder={f.placeholder}
                  onChange={setParam(f.name)}
                />
              </div>
            ))}
          </div>

          {kind === "comment" && (
            <>
              <label>Target post URL <span className="muted">(optional — for your reference)</span></label>
              <input value={postUrl} placeholder="https://linkedin.com/posts/…"
                     onChange={(e) => setPostUrl(e.target.value)} />
              <label>Company-page comment ID <span className="muted">(optional — enables auto-reply)</span></label>
              <input value={commentId} placeholder="leave blank for a personal comment you'll post yourself"
                     onChange={(e) => setCommentId(e.target.value)} />
              {commentId.trim() && (
                <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, fontWeight: 400 }}>
                  <input type="checkbox" checked={autoSend} style={{ width: "auto" }}
                         onChange={(e) => setAutoSend(e.target.checked)} />
                  <span>Auto-post this reply (no manual approval). Company-page comments only — LinkedIn's API doesn't allow auto-sending personal comments or DMs.</span>
                </label>
              )}
            </>
          )}

          {accounts.length > 0 && (
            <>
              <label>Account <span className="muted">(optional)</span></label>
              <select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
                <option value="">— none —</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.display_name || a.zernio_account_id} ({a.account_type})
                  </option>
                ))}
              </select>
            </>
          )}

          {error && <div className="error">{error}</div>}
          <div className="row" style={{ marginTop: 14 }}>
            <button className="btn-primary" disabled={busy} type="submit">
              {busy ? "Drafting…" : "Generate draft"}
            </button>
          </div>
        </form>
      </div>

      <div className="row" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0, color: "var(--blue)" }}>Inbox</h2>
        <div className="spacer" />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ width: 160 }}>
          <option value="pending">Pending</option>
          <option value="approved">Ready to send</option>
          <option value="sent">Sent</option>
          <option value="rejected">Rejected</option>
          <option value="all">All</option>
        </select>
        <button className="btn-secondary" onClick={load}>Refresh</button>
      </div>

      {loading ? (
        <div className="empty">Loading…</div>
      ) : items.length === 0 ? (
        <div className="empty">Nothing here. Draft an action above.</div>
      ) : (
        items.map((it) => <InboxCard key={it.id} item={it} onChange={load} />)
      )}
    </>
  );
}
