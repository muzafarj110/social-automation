import { useEffect, useState } from "react";
import { studioRun } from "../api.js";

const IMAGE_TOOLS = new Set(["social_card", "ad_creative", "infographic"]);
const LONG_FORM_TOOLS = new Set([
  "linkedin_article", "linkedin_carousel", "linkedin_newsletter",
  "post_series", "outreach_campaign", "linkedin_brand_audit", "linkedin_repurpose",
]);
function toolCost(key) {
  if (IMAGE_TOOLS.has(key)) return 5;
  if (LONG_FORM_TOOLS.has(key)) return 2;
  return 1;
}

// Tool catalog — grouped by category. `a` = textarea, `n` = number, else text.
const CATEGORIES = [
  {
    name: "Reports & insights",
    tools: {
      marketing_report: { label: "Marketing report", blurb: "Performance report + what to do next.",
        fields: [["metrics_data", "Paste your metrics (or describe them)", true, "a"], ["period", "Period"], ["channel", "Channel"]] },
      ab_test: { label: "A/B test analysis", blurb: "Compare two variants, get a winner.",
        fields: [["variant_a", "Variant A", true, "a"], ["variant_b", "Variant B", true, "a"], ["metric", "Primary metric"]] },
      funnel_gap: { label: "Funnel gap finder", blurb: "Find where your funnel leaks.",
        fields: [["funnel_data", "Funnel metrics (traffic, leads, conversions…)", true, "a"], ["business_type", "Business type"]] },
    },
  },
  {
    name: "Email",
    tools: {
      email_sequence: { label: "Email sequence", blurb: "Welcome, nurture or sales series.",
        fields: [["product", "Product / service", true], ["sequence_type", "Type (welcome/nurture/sales)"], ["audience", "Audience"], ["num_emails", "Number of emails", false, "n"]] },
      subject_line: { label: "Subject-line optimizer", blurb: "Punch up a subject line.",
        fields: [["subject_line", "Current subject line", true], ["email_type", "Email type"], ["audience", "Audience"]] },
      cold_outreach: { label: "Cold outreach email", blurb: "A cold email to a prospect.",
        fields: [["product", "Your offer", true], ["prospect_role", "Prospect's role", true], ["pain_point", "Known pain point"], ["tone", "Tone"]] },
    },
  },
  {
    name: "SEO & blog",
    tools: {
      content_writing: { label: "Blog / article", blurb: "Long-form SEO content.",
        fields: [["topic", "Topic", true], ["keywords", "Keywords"], ["content_type", "Type (blog/article/landing)"], ["tone", "Tone"], ["word_count", "Word count", false, "n"]] },
      keyword_research: { label: "Keyword research", blurb: "Keywords to target.",
        fields: [["topic", "Topic / seed keyword", true], ["goal", "Goal"], ["market", "Market"]] },
      technical_seo: { label: "Technical SEO audit", blurb: "On-page / technical fixes.",
        fields: [["target", "URL or page description", true], ["page_type", "Page type"], ["primary_keyword", "Primary keyword"]] },
    },
  },
  {
    name: "LinkedIn formats",
    tools: {
      linkedin_article: { label: "Article", blurb: "Long-form LinkedIn article.",
        fields: [["topic", "Topic", true], ["audience", "Audience", true], ["angle", "Angle"], ["word_count", "Word count", false, "n"]] },
      linkedin_carousel: { label: "Carousel", blurb: "A multi-slide carousel.",
        fields: [["topic", "Topic", true], ["audience", "Audience", true], ["goal", "Goal"], ["num_slides", "Slides", false, "n"]] },
      linkedin_newsletter: { label: "Newsletter", blurb: "A newsletter issue.",
        fields: [["topic", "Topic", true], ["audience", "Audience", true], ["newsletter_name", "Newsletter name"], ["tone", "Tone"]] },
      linkedin_poll: { label: "Poll", blurb: "An engagement poll.",
        fields: [["topic", "Topic", true], ["audience", "Audience", true], ["goal", "Goal"], ["poll_type", "Poll type"]] },
      linkedin_video: { label: "Video script", blurb: "A short video script.",
        fields: [["topic", "Topic", true], ["audience", "Audience", true], ["goal", "Goal"], ["duration", "Seconds", false, "n"], ["style", "Style"]] },
      linkedin_repurpose: { label: "Repurpose", blurb: "Turn content into a post.",
        fields: [["original_content", "Original content", true, "a"], ["source_type", "Source type"], ["target_audience", "Audience"]] },
      linkedin_url_post: { label: "URL → post", blurb: "Turn a link into a post.",
        fields: [["url", "Article / page URL", true], ["audience", "Audience"], ["tone", "Tone"]] },
      linkedin_story_arc: { label: "Story post", blurb: "A personal story + lesson.",
        fields: [["experience", "The experience / event", true, "a"], ["lesson", "What you learned", true], ["story_type", "Type"]] },
      linkedin_hooks: { label: "Hooks", blurb: "Scroll-stopping opening lines.",
        fields: [["topic", "Topic", true], ["niche", "Niche"], ["audience", "Audience"]] },
      post_series: { label: "Post series", blurb: "A connected multi-post series.",
        fields: [["topic", "Topic", true], ["audience", "Audience"], ["series_length", "Posts", false, "n"], ["series_goal", "Goal"]] },
      outreach_campaign: { label: "Outreach sequence", blurb: "A multi-touch outreach sequence.",
        fields: [["your_offer", "Your offer", true], ["target_role", "Target role", true], ["num_touchpoints", "Touchpoints", false, "n"]] },
      linkedin_brand_audit: { label: "Profile brand audit", blurb: "Score & improve your brand.",
        fields: [["headline", "Headline", true], ["about_section", "About section", true, "a"], ["niche", "Niche"], ["goal", "Goal"]] },
    },
  },
  {
    name: "Graphics",
    tools: {
      social_card: { label: "Social graphic", blurb: "A branded graphic from text.",
        fields: [["text", "The message / quote", true, "a"], ["theme", "Theme (modern/bold/minimal…)"], ["brand_name", "Brand name"]] },
      ad_creative: { label: "Ad creative", blurb: "Ad copy + matching image.",
        fields: [["product", "Product / service", true], ["offer", "Offer"], ["platform", "Platform"], ["count", "Variations", false, "n"]] },
      infographic: { label: "Infographic", blurb: "An infographic image from points.",
        fields: [["topic", "Topic", true], ["content_points", "Key points to visualize", true, "a"], ["infographic_type", "Type"], ["color_scheme", "Color scheme"], ["brand_name", "Brand name"]] },
    },
  },
];

// Module-level cache so results + in-flight generations + the selected tool
// survive switching tools, switching app tabs (unmount), and coming back.
const FIRST = Object.keys(CATEGORIES[0].tools)[0];
const CACHE = { result: {}, inflight: {}, cat: 0, tool: FIRST, form: {} };

function findCat(toolKey) {
  return Math.max(0, CATEGORIES.findIndex((c) => toolKey in c.tools));
}

// Heuristic renderer: turns arbitrary Hub model JSON into polished cards —
// titles, colored pills (intent/competition/ROI…), summaries, and lists.
const BADGE_KEYS = ["intent", "competition", "difficulty", "priority", "impact", "grade", "sentiment", "status", "roi_score", "roi", "score", "viral_score", "viral_grade", "funnel_stage"];
const TITLE_KEYS = ["keyword", "title", "headline", "name", "hook", "subject_line", "subject", "episode", "touchpoint", "day", "question", "slide_type", "step", "phase", "variant", "recommended_variant", "label"];
const BODY_KEYS = ["why", "description", "reason", "rationale", "text", "body", "full_post", "message", "content", "subtext", "tip", "explanation", "caption", "analysis", "recommendation", "insight", "strategy", "note", "details"];

const pretty = (k) => k.replace(/_/g, " ");
const isScalar = (v) => v === null || ["string", "number", "boolean"].includes(typeof v);

function pillClass(k, v) {
  const s = String(v).toLowerCase();
  if (k === "competition" || k === "difficulty") return s.includes("high") ? "failed" : s.includes("med") ? "pending" : "published";
  if (k === "priority" || k === "impact") return s.includes("high") ? "published" : s.includes("low") ? "draft" : "pending";
  if (k === "intent") return "scheduled";
  return "kind";
}
function pillText(k, v) {
  if (k === "roi_score" || k === "roi") return `ROI ${v}/10`;
  if (k === "score") return `Score ${v}`;
  if (k === "viral_score") return `${v}/100`;
  return String(v);
}

function Item({ obj }) {
  const entries = Object.entries(obj).filter(([k, v]) => !k.startsWith("_") && v !== null && v !== "");
  const titleEntry = TITLE_KEYS.map((k) => entries.find(([ek]) => ek === k)).find(Boolean);
  const pills = entries.filter(([k, v]) => BADGE_KEYS.includes(k) && isScalar(v));
  const bodies = entries.filter(([k, v]) => BODY_KEYS.includes(k) && typeof v === "string");
  const used = new Set([titleEntry && titleEntry[0], ...pills.map((p) => p[0]), ...bodies.map((b) => b[0])]);
  const rest = entries.filter(([k]) => !used.has(k));
  return (
    <div className="res-item">
      {(titleEntry || pills.length > 0) && (
        <div className="res-item-head">
          {titleEntry && <div className="res-item-title">{String(titleEntry[1])}</div>}
          {pills.length > 0 && (
            <div className="res-pills">
              {pills.map(([k, v]) => <span key={k} className={`badge ${pillClass(k, v)}`} title={pretty(k)}>{pillText(k, v)}</span>)}
            </div>
          )}
        </div>
      )}
      {bodies.map(([k, v]) => <div key={k} className="res-body">{v}</div>)}
      {rest.map(([k, v]) => (
        isScalar(v)
          ? <div key={k} className="res-kv"><b>{pretty(k)}:</b> {String(v)}</div>
          : <div key={k} style={{ marginTop: 6 }}><div className="res-kv"><b>{pretty(k)}</b></div><Value v={v} /></div>
      ))}
    </div>
  );
}

function Value({ v }) {
  if (isScalar(v)) return <p className="res-body">{String(v)}</p>;
  if (Array.isArray(v)) {
    if (v.every(isScalar)) return <ul className="res-list">{v.map((x, i) => <li key={i}>{String(x)}</li>)}</ul>;
    return <div>{v.map((x, i) => <Item key={i} obj={x} />)}</div>;
  }
  return <Item obj={v} />;
}

function Result({ data }) {
  const entries = Object.entries(data).filter(([k, v]) => !k.startsWith("_") && k !== "image_url" && k !== "html" && v !== null && v !== "");
  return (
    <div>
      {entries.map(([k, v]) => {
        const summaryish = /summary|overview/i.test(k) && typeof v === "string";
        return (
          <div key={k} className="res-section">
            <div className="res-h">{pretty(k)}</div>
            {summaryish ? <div className="res-callout">{v}</div> : <Value v={v} />}
          </div>
        );
      })}
    </div>
  );
}

export default function Studio() {
  const [cat, setCat] = useState(CACHE.cat);
  const [toolKey, setToolKey] = useState(CACHE.tool);
  const [form, setForm] = useState(CACHE.form[CACHE.tool] || {});
  const [result, setResult] = useState(CACHE.result[CACHE.tool] || null);
  const [busy, setBusy] = useState(Boolean(CACHE.inflight[CACHE.tool]));
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const tools = CATEGORIES[cat].tools;
  const tool = tools[toolKey];

  // Load the selected tool's cached result, and re-attach to any in-flight run.
  useEffect(() => {
    setResult(CACHE.result[toolKey] || null);
    setError(""); setCopied(false);
    const p = CACHE.inflight[toolKey];
    if (p) {
      setBusy(true);
      p.then((data) => { if (CACHE.tool === toolKey) { setResult(data); setBusy(false); } })
       .catch((e) => { if (CACHE.tool === toolKey) { setError(e.message); setBusy(false); } });
    } else {
      setBusy(false);
    }
  }, [toolKey]); // eslint-disable-line

  const pickCat = (i) => { const k = Object.keys(CATEGORIES[i].tools)[0]; setCat(i); CACHE.cat = i; selectTool(k); };
  const selectTool = (k) => { setToolKey(k); CACHE.tool = k; setForm(CACHE.form[k] || {}); };
  const pickTool = (k) => { setCat(findCat(k)); CACHE.cat = findCat(k); selectTool(k); };
  const set = (name) => (e) => {
    const f = { ...form, [name]: e.target.value };
    setForm(f); CACHE.form[toolKey] = f;
  };

  const run = async (e) => {
    e.preventDefault();
    setError(""); setCopied(false); setResult(null);
    try {
      for (const f of tool.fields) if (f[2] && !(form[f[0]] || "").trim()) throw new Error(`${f[1]} is required.`);
      const params = {};
      for (const f of tool.fields) {
        const raw = form[f[0]];
        if (raw === undefined || String(raw).trim() === "") continue;
        params[f[0]] = f[3] === "n" ? Number(raw) : raw;
      }
      const key = toolKey;
      setBusy(true);
      // Cache the promise so the result survives tab/tool switches.
      const p = studioRun(key, params).then((res) => {
        CACHE.result[key] = res.data; delete CACHE.inflight[key]; return res.data;
      }).catch((err) => { delete CACHE.inflight[key]; throw err; });
      CACHE.inflight[key] = p;
      const data = await p;
      if (CACHE.tool === key) { setResult(data); setBusy(false); }
    } catch (e2) {
      setError(e2.message); setBusy(false);
    }
  };

  const imageUrl = result?.image_url;

  return (
    <>
      {error && <div className="flash error">{error}</div>}

      <div className="card">
        <h2>Marketing Studio</h2>
        <p className="muted" style={{ marginTop: -6 }}>LinkedIn formats, graphics and long-form content. Text = 1 credit · Long-form = 2 credits · Images = 5 credits.</p>
        <div className="seg" style={{ marginTop: 4 }}>
          {CATEGORIES.map((c, i) => (
            <button key={c.name} className={cat === i ? "btn-primary" : "btn-secondary"} onClick={() => pickCat(i)}>{c.name}</button>
          ))}
        </div>
        <div className="tool-tiles">
          {Object.entries(tools).map(([k, t]) => {
            const cost = toolCost(k);
            return (
              <div key={k} className={`tool-tile${toolKey === k ? " active" : ""}`} onClick={() => selectTool(k)}>
                <div className="row" style={{ alignItems: "center", marginBottom: 2 }}>
                  <div className="tt-name" style={{ flex: 1 }}>{t.label}</div>
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 999,
                    background: cost >= 5 ? "#fce0f7" : cost >= 2 ? "#dbe8ff" : "#d1faf4",
                    color: cost >= 5 ? "#901d86" : cost >= 2 ? "#2352b8" : "#1f7a72",
                    flexShrink: 0,
                  }}>{cost}cr</span>
                </div>
                <div className="tt-blurb">{t.blurb}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card">
        <h2>{tool.label}</h2>
        <p className="muted" style={{ marginTop: -6 }}>{tool.blurb}</p>
        <form onSubmit={run}>
          <div className="grid-2">
            {tool.fields.map((f) => (
              <div key={f[0]} style={f[3] === "a" ? { gridColumn: "1 / -1" } : undefined}>
                <label>{f[1]} {f[2] ? <span style={{ color: "var(--teal)" }}>*</span> : <span className="muted">(optional)</span>}</label>
                {f[3] === "a"
                  ? <textarea value={form[f[0]] || ""} onChange={set(f[0])} style={{ minHeight: 90 }} />
                  : <input type={f[3] === "n" ? "number" : "text"} value={form[f[0]] || ""} onChange={set(f[0])} />}
              </div>
            ))}
          </div>
          <div className="row" style={{ marginTop: 12, alignItems: "center" }}>
            <button className="btn-primary" type="submit" disabled={busy}>
              {busy ? "Generating…" : `Generate (${toolCost(toolKey)} credit${toolCost(toolKey) > 1 ? "s" : ""})`}
            </button>
            {IMAGE_TOOLS.has(toolKey) && (
              <span className="muted" style={{ fontSize: 12.5 }}>🎨 Image generation — higher cost</span>
            )}
            {LONG_FORM_TOOLS.has(toolKey) && (
              <span className="muted" style={{ fontSize: 12.5 }}>📄 Long-form content — 2 credits</span>
            )}
          </div>
        </form>
      </div>

      {(busy || result) && (
        <div className="card">
          <h2>{tool.label} — result</h2>
          {busy ? (
            <div className="studio-loading"><span className="spinner" />Generating {tool.label}… you can switch tabs; it'll be here when you're back.</div>
          ) : (
            <>
              {imageUrl && (
                <div style={{ marginBottom: 14 }}>
                  <img src={imageUrl} alt={tool.label} style={{ maxWidth: "100%", borderRadius: 12, border: "1px solid var(--line)" }} />
                  <div className="row" style={{ marginTop: 10 }}>
                    <input readOnly value={imageUrl} style={{ flex: 1 }} onFocus={(e) => e.target.select()} />
                    <button className="btn-secondary" type="button"
                      onClick={() => { navigator.clipboard?.writeText(imageUrl); setCopied(true); }}>
                      {copied ? "Copied!" : "Copy image URL"}
                    </button>
                  </div>
                  <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                    To publish this image: open <strong>Posts</strong>, edit a draft, and paste this URL as its media.
                  </p>
                </div>
              )}
              <Result data={result} />
            </>
          )}
        </div>
      )}
    </>
  );
}
