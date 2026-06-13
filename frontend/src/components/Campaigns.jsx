import { useEffect, useState } from "react";
import {
  listCampaigns,
  createCampaign,
  updateCampaign,
  deleteCampaign,
  runCampaign,
  listCampaignPosts,
  publishPost,
  deletePost,
} from "../api.js";

function CampaignPosts({ campaignId }) {
  const [posts, setPosts] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(0);

  const load = async () => {
    try { setPosts(await listCampaignPosts(campaignId)); } catch (e) { setErr(e.message); }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line
  const act = (id, fn) => async () => {
    setErr(""); setBusy(id);
    try { await fn(); await load(); } catch (e) { setErr(e.message); } finally { setBusy(0); }
  };

  if (err) return <div className="error">{err}</div>;
  if (!posts) return <div className="muted" style={{ padding: "8px 0" }}>Loading…</div>;
  if (!posts.length) return <div className="muted" style={{ padding: "8px 0" }}>No posts generated yet — hit “Run now”.</div>;
  return (
    <div className="pill-list" style={{ marginTop: 10 }}>
      {posts.map((p) => (
        <div className="pill" key={p.id} style={{ flexDirection: "column", alignItems: "stretch", gap: 6 }}>
          <div className="row">
            <span className={`badge ${p.status}`}>{p.status}</span>
            {p.scheduled_for && <span className="muted" style={{ fontSize: 12 }}>for {new Date(p.scheduled_for).toLocaleString()}</span>}
            <div className="spacer" />
            {p.platform_post_url && <a href={p.platform_post_url} target="_blank" rel="noreferrer" style={{ color: "var(--teal)", fontSize: 12, fontWeight: 600 }}>View ↗</a>}
          </div>
          <div style={{ fontSize: 13, whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{p.body.slice(0, 280)}{p.body.length > 280 ? "…" : ""}</div>
          {(p.status === "draft" || p.status === "failed") && (
            <div className="row">
              <button className="btn-primary" style={{ padding: "5px 12px" }} disabled={busy === p.id} onClick={act(p.id, () => publishPost(p.id))}>Publish now</button>
              <button className="btn-danger" style={{ padding: "5px 12px" }} disabled={busy === p.id} onClick={act(p.id, () => deletePost(p.id))}>Discard</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

const POST_TYPES = [
  "Personal Story + Lesson",
  "Contrarian Take",
  "How-to / Tips",
  "Industry Insight",
  "Case Study",
];
const WEEKDAYS = [["Mon", 0], ["Tue", 1], ["Wed", 2], ["Thu", 3], ["Fri", 4], ["Sat", 5], ["Sun", 6]];
const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

// Platforms the app can post to (mirrors backend app/core/platforms.py).
const PLATFORMS = [
  ["linkedin", "LinkedIn"], ["twitter", "X (Twitter)"], ["instagram", "Instagram"],
  ["facebook", "Facebook"], ["tiktok", "TikTok"], ["youtube", "YouTube"],
  ["pinterest", "Pinterest"], ["reddit", "Reddit"], ["bluesky", "Bluesky"],
  ["threads", "Threads"], ["googlebusiness", "Google Business"], ["telegram", "Telegram"],
  ["snapchat", "Snapchat"], ["whatsapp", "WhatsApp"], ["discord", "Discord"],
];

const emptyForm = {
  name: "",
  account_id: "",
  platforms: [],
  mode: "approve",
  topic_source: "topics",
  topicsText: "",
  niche: "",
  goal: "",
  audience: "early-stage founders",
  tone: "professional but human",
  post_types: [POST_TYPES[0]],
  frequency_per_week: 3,
  days: [0, 2, 4],
  time_of_day: "09:00",
  timezone: browserTz,
  ai_timing: true,
  auto_improve: true,
  with_infographic: false,
  learn_from_analytics: false,
};

function CampaignCard({ c, onChange, goTab }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [ranCount, setRanCount] = useState(null);
  const [error, setError] = useState("");
  const [showPosts, setShowPosts] = useState(false);
  const [refreshPosts, setRefreshPosts] = useState(0);

  const run = (fn) => async () => {
    setBusy(true); setError(""); setMsg(""); setRanCount(null);
    try { await fn(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const doRun = run(async () => {
    const posts = await runCampaign(c.id);
    const n = posts.length;
    setMsg(c.mode === "auto"
      ? `Generated ${n} post${n === 1 ? "" : "s"} and scheduled them.`
      : `Generated ${n} draft${n === 1 ? "" : "s"} — review them below before publishing.`);
    setRanCount(n);
    setShowPosts(true);
    setRefreshPosts((x) => x + 1);
    onChange();
  });
  const togglePause = run(async () => {
    await updateCampaign(c.id, { status: c.status === "active" ? "paused" : "active" });
    onChange();
  });
  const remove = run(async () => { await deleteCampaign(c.id); onChange(); });

  return (
    <div className="card">
      <div className="row">
        <strong style={{ color: "var(--blue)" }}>{c.name}</strong>
        <span className={`badge ${c.status === "active" ? "published" : "draft"}`}>{c.status}</span>
        <span className="badge kind">{c.mode === "auto" ? "auto-publish" : "approve first"}</span>
        {c.auto_improve && <span className="badge published">QA + polish</span>}
        {c.learn_from_analytics && <span className="badge published">learns from analytics</span>}
        <div className="spacer" />
        <span className="muted">{c.frequency_per_week}×/week</span>
      </div>
      <div className="muted" style={{ marginTop: 6 }}>
        {c.topic_source === "goal"
          ? `Goal: ${c.goal || c.niche || "—"}`
          : `Topics: ${(c.topics || []).join(", ") || "—"}`}
        {" · "}
        {c.ai_timing
          ? "AI-picked times"
          : `${(c.days || []).map((d) => WEEKDAYS[d]?.[0]).join("/")} at ${c.time_of_day} (${c.timezone})`}
        {" · "}{(c.post_types || [c.post_type]).length} angle
        {(c.post_types || [c.post_type]).length === 1 ? "" : "s"}
      </div>
      {c.last_error && <div className="error">{c.last_error}</div>}
      {error && <div className="error">{error}</div>}
      {msg && (
        <div className="success" style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span>{msg}</span>
          {ranCount > 0 && goTab && (
            <button className="btn-secondary" style={{ padding: "4px 10px" }} onClick={() => goTab("posts")}>
              Review in Posts →
            </button>
          )}
        </div>
      )}
      <div className="row" style={{ marginTop: 12 }}>
        <button className="btn-primary" disabled={busy} onClick={doRun}>Run now</button>
        <button className="btn-secondary" disabled={busy} onClick={() => setShowPosts((v) => !v)}>
          {showPosts ? "Hide posts" : "Review posts"}
        </button>
        <button className="btn-secondary" disabled={busy} onClick={togglePause}>
          {c.status === "active" ? "Pause" : "Resume"}
        </button>
        <div className="spacer" />
        <button className="btn-danger" disabled={busy} onClick={remove}>Delete</button>
      </div>

      {showPosts && (
        <div style={{ marginTop: 12, borderTop: "1px solid var(--line)", paddingTop: 12 }}>
          <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
            What this campaign generated — review and publish before it goes live.
          </div>
          <CampaignPosts key={refreshPosts} campaignId={c.id} />
        </div>
      )}
    </div>
  );
}

export default function Campaigns({ accounts, goTab }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try { setItems(await listCampaigns()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []); // eslint-disable-line
  useEffect(() => {
    if (!form.account_id && accounts.length) setForm((f) => ({ ...f, account_id: accounts[0].id }));
  }, [accounts]); // eslint-disable-line

  // Platforms the user actually has a connected account on (unique, ordered).
  const connectedPlatforms = [...new Set(accounts.map((a) => a.platform || "linkedin"))];
  const platformLabel = Object.fromEntries(PLATFORMS);

  // Default the platform selection to the chosen account's platform.
  useEffect(() => {
    const acc = accounts.find((a) => String(a.id) === String(form.account_id));
    if (acc && form.platforms.length === 0) {
      setForm((f) => ({ ...f, platforms: [acc.platform || "linkedin"] }));
    }
  }, [form.account_id, accounts]); // eslint-disable-line

  const togglePlatform = (p) =>
    setForm((f) => {
      const has = f.platforms.includes(p);
      if (has && f.platforms.length === 1) return f; // keep at least one
      return { ...f, platforms: has ? f.platforms.filter((x) => x !== p) : [...f.platforms, p] };
    });

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const toggleDay = (d) =>
    setForm((f) => ({
      ...f,
      days: f.days.includes(d) ? f.days.filter((x) => x !== d) : [...f.days, d].sort(),
    }));
  const toggleAngle = (t) =>
    setForm((f) => {
      const has = f.post_types.includes(t);
      // keep at least one angle selected
      if (has && f.post_types.length === 1) return f;
      return { ...f, post_types: has ? f.post_types.filter((x) => x !== t) : [...f.post_types, t] };
    });

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setMsg(""); setBusy(true);
    try {
      if (!form.account_id) throw new Error("Pick a social account.");
      const payload = {
        name: form.name.trim(),
        account_id: Number(form.account_id),
        platforms: form.platforms,
        mode: form.mode,
        topic_source: form.topic_source,
        tone: form.tone,
        post_type: form.post_types[0],
        post_types: form.post_types,
        audience: form.audience || null,
        frequency_per_week: Number(form.frequency_per_week),
        days: form.days,
        time_of_day: form.time_of_day,
        timezone: form.timezone,
        ai_timing: form.ai_timing,
        auto_improve: form.auto_improve,
        with_infographic: form.with_infographic,
        learn_from_analytics: form.learn_from_analytics,
      };
      if (form.topic_source === "topics") {
        payload.topics = form.topicsText.split("\n").map((s) => s.trim()).filter(Boolean);
        if (!payload.topics.length) throw new Error("Add at least one topic (one per line).");
      } else {
        payload.niche = form.niche.trim();
        payload.goal = form.goal.trim();
        if (!payload.niche && !payload.goal) throw new Error("Add a niche or a goal.");
      }
      await createCampaign(payload);
      setMsg("Campaign created. Use “Run now” to generate the first batch.");
      setForm({ ...emptyForm, account_id: form.account_id, timezone: form.timezone });
      load();
    } catch (e2) {
      setError(e2.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="card">
        <h2>New campaign</h2>
        {accounts.length === 0 && (
          <div className="error">Link a social account first (Accounts tab).</div>
        )}
        <form onSubmit={submit}>
          <div className="grid-2">
            <div>
              <label>Name</label>
              <input value={form.name} onChange={set("name")} placeholder="My weekly thought leadership" />
            </div>
            {accounts.length > 0 && (
              <div>
                <label>Account</label>
                <select value={form.account_id} onChange={set("account_id")}>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.display_name || a.zernio_account_id} ({a.account_type})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {connectedPlatforms.length > 0 && (
            <>
              <label>Post to platforms</label>
              <div className="seg" style={{ flexWrap: "wrap" }}>
                {connectedPlatforms.map((p) => (
                  <button type="button" key={p}
                    className={form.platforms.includes(p) ? "btn-primary" : "btn-secondary"}
                    onClick={() => togglePlatform(p)}>
                    {platformLabel[p] || p}
                  </button>
                ))}
              </div>
              <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                One idea per slot is tailored by AI to each selected platform. Connect more accounts (Accounts tab) to post to more platforms.
              </p>
            </>
          )}

          <label>Automation level</label>
          <div className="seg">
            <button type="button" className={form.mode === "approve" ? "btn-primary" : "btn-secondary"}
              onClick={() => setForm({ ...form, mode: "approve" })}>Approve first</button>
            <button type="button" className={form.mode === "auto" ? "btn-primary" : "btn-secondary"}
              onClick={() => setForm({ ...form, mode: "auto" })}>Auto-publish</button>
          </div>
          <div className="muted" style={{ marginTop: 4 }}>
            {form.mode === "auto"
              ? "Posts are generated and scheduled to LinkedIn automatically (needs your Zernio key)."
              : "Posts are generated as drafts for you to review and schedule."}
          </div>

          <label style={{ marginTop: 12 }}>Topic source</label>
          <div className="seg">
            <button type="button" className={form.topic_source === "topics" ? "btn-primary" : "btn-secondary"}
              onClick={() => setForm({ ...form, topic_source: "topics" })}>My topics</button>
            <button type="button" className={form.topic_source === "goal" ? "btn-primary" : "btn-secondary"}
              onClick={() => setForm({ ...form, topic_source: "goal" })}>From a goal</button>
          </div>

          {form.topic_source === "topics" ? (
            <>
              <label>Topics (one per line)</label>
              <textarea value={form.topicsText} onChange={set("topicsText")} style={{ minHeight: 90 }}
                placeholder={"Lessons from scaling a startup\nWhy most marketing fails\nAI tools I use daily"} />
            </>
          ) : (
            <div className="grid-2">
              <div>
                <label>Niche</label>
                <input value={form.niche} onChange={set("niche")} placeholder="AI consulting for SMBs" />
              </div>
              <div>
                <label>Goal</label>
                <input value={form.goal} onChange={set("goal")} placeholder="grow following and generate leads" />
              </div>
            </div>
          )}

          <div className="grid-2">
            <div>
              <label>Audience</label>
              <input value={form.audience} onChange={set("audience")} placeholder="early-stage founders" />
            </div>
            <div>
              <label>Tone</label>
              <input value={form.tone} onChange={set("tone")} />
            </div>
          </div>

          <label>Content angles to rotate <span className="muted">(pick one or more)</span></label>
          <div className="row">
            {POST_TYPES.map((t) => (
              <button type="button" key={t}
                className={form.post_types.includes(t) ? "btn-primary" : "btn-secondary"}
                onClick={() => toggleAngle(t)} style={{ padding: "8px 12px" }}>{t}</button>
            ))}
          </div>

          <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12, fontWeight: 400 }}>
            <input type="checkbox" checked={form.auto_improve} style={{ width: "auto" }}
                   onChange={(e) => setForm({ ...form, auto_improve: e.target.checked })} />
            <span>Auto quality-check &amp; polish each post before it's scheduled <span className="muted">(recommended)</span></span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, fontWeight: 400 }}>
            <input type="checkbox" checked={form.with_infographic} style={{ width: "auto" }}
                   onChange={(e) => setForm({ ...form, with_infographic: e.target.checked })} />
            <span>Generate an infographic for each post <span className="muted">(preview/download from Posts; not auto-attached to LinkedIn yet)</span></span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, fontWeight: 400 }}>
            <input type="checkbox" checked={form.learn_from_analytics} style={{ width: "auto" }}
                   onChange={(e) => setForm({ ...form, learn_from_analytics: e.target.checked })} />
            <span>Learn from analytics <span className="muted">(double down on your best-performing past posts — needs your Zernio key)</span></span>
          </label>

          <label>Posts per week</label>
          <input type="number" min="1" max="14" value={form.frequency_per_week}
            onChange={set("frequency_per_week")} style={{ width: 100 }} />

          <label style={{ marginTop: 12 }}>Posting times</label>
          <div className="seg">
            <button type="button" className={form.ai_timing ? "btn-primary" : "btn-secondary"}
              onClick={() => setForm({ ...form, ai_timing: true })}>Let AI decide</button>
            <button type="button" className={!form.ai_timing ? "btn-primary" : "btn-secondary"}
              onClick={() => setForm({ ...form, ai_timing: false })}>I'll choose</button>
          </div>

          {form.ai_timing ? (
            <div className="muted" style={{ marginTop: 6 }}>
              The Hub's engagement-strategy model suggests the best days/times for your niche.
            </div>
          ) : (
            <>
              <label>Days</label>
              <div className="row">
                {WEEKDAYS.map(([lbl, d]) => (
                  <button type="button" key={d}
                    className={form.days.includes(d) ? "btn-primary" : "btn-secondary"}
                    onClick={() => toggleDay(d)} style={{ padding: "8px 12px" }}>{lbl}</button>
                ))}
              </div>
              <div className="row">
                <div>
                  <label>Time of day</label>
                  <input type="time" value={form.time_of_day} onChange={set("time_of_day")} style={{ width: 140 }} />
                </div>
                <div style={{ flex: 1 }}>
                  <label>Timezone</label>
                  <input value={form.timezone} onChange={set("timezone")} />
                </div>
              </div>
            </>
          )}

          {error && <div className="error">{error}</div>}
          {msg && <div className="success">{msg}</div>}
          <div className="row" style={{ marginTop: 14 }}>
            <button className="btn-primary" type="submit" disabled={busy || accounts.length === 0}>
              {busy ? "Saving…" : "Create campaign"}
            </button>
          </div>
        </form>
      </div>

      <div className="row" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0, color: "var(--blue)" }}>Your campaigns</h2>
        <div className="spacer" />
        <button className="btn-secondary" onClick={load}>Refresh</button>
      </div>
      {loading ? (
        <div className="empty">Loading…</div>
      ) : items.length === 0 ? (
        <div className="empty">No campaigns yet. Create one above to put posting on autopilot.</div>
      ) : (
        items.map((c) => <CampaignCard key={c.id} c={c} onChange={load} goTab={goTab} />)
      )}
    </>
  );
}
