import { useState } from "react";
import { studioRun } from "../api.js";

// Tool catalog — grouped by category. `a` = textarea, `n` = number, else text.
const CATEGORIES = [
  {
    name: "Reports & insights",
    tools: {
      marketing_report: { label: "Marketing report", blurb: "A full performance report with what's working and what to do next.",
        fields: [["metrics_data", "Paste your metrics (or describe them)", true, "a"], ["period", "Period"], ["channel", "Channel"]] },
      ab_test: { label: "A/B test analysis", blurb: "Compare two variants and get a recommendation.",
        fields: [["variant_a", "Variant A", true, "a"], ["variant_b", "Variant B", true, "a"], ["metric", "Primary metric"]] },
      funnel_gap: { label: "Funnel gap finder", blurb: "Find where your funnel leaks.",
        fields: [["funnel_data", "Funnel metrics (traffic, leads, conversions…)", true, "a"], ["business_type", "Business type"]] },
    },
  },
  {
    name: "Email",
    tools: {
      email_sequence: { label: "Email sequence", blurb: "A multi-email sequence (welcome, nurture, sales…).",
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
      technical_seo: { label: "Technical SEO audit", blurb: "On-page / technical recommendations.",
        fields: [["target", "URL or page description", true], ["page_type", "Page type"], ["primary_keyword", "Primary keyword"]] },
    },
  },
  {
    name: "LinkedIn formats",
    tools: {
      linkedin_article: { label: "Article", blurb: "A long-form LinkedIn article.",
        fields: [["topic", "Topic", true], ["audience", "Audience", true], ["angle", "Angle"], ["word_count", "Word count", false, "n"]] },
      linkedin_carousel: { label: "Carousel / document", blurb: "A multi-slide carousel.",
        fields: [["topic", "Topic", true], ["audience", "Audience", true], ["goal", "Goal"], ["num_slides", "Slides", false, "n"]] },
      linkedin_newsletter: { label: "Newsletter", blurb: "A LinkedIn newsletter issue.",
        fields: [["topic", "Topic", true], ["audience", "Audience", true], ["newsletter_name", "Newsletter name"], ["tone", "Tone"]] },
      linkedin_poll: { label: "Poll", blurb: "An engagement poll.",
        fields: [["topic", "Topic", true], ["audience", "Audience", true], ["goal", "Goal"], ["poll_type", "Poll type"]] },
      linkedin_video: { label: "Video script", blurb: "A short video script.",
        fields: [["topic", "Topic", true], ["audience", "Audience", true], ["goal", "Goal"], ["duration", "Seconds", false, "n"], ["style", "Style"]] },
      linkedin_repurpose: { label: "Repurpose content", blurb: "Turn existing content into a LinkedIn post.",
        fields: [["original_content", "Original content", true, "a"], ["source_type", "Source type"], ["target_audience", "Audience"]] },
      linkedin_url_post: { label: "URL → post", blurb: "Turn a link into a post.",
        fields: [["url", "Article / page URL", true], ["audience", "Audience"], ["tone", "Tone"]] },
      linkedin_story_arc: { label: "Story post", blurb: "A personal story + lesson.",
        fields: [["experience", "The experience / event", true, "a"], ["lesson", "What you learned", true], ["story_type", "Type"]] },
      linkedin_hooks: { label: "Hooks", blurb: "Scroll-stopping opening lines.",
        fields: [["topic", "Topic", true], ["niche", "Niche"], ["audience", "Audience"]] },
      post_series: { label: "Post series", blurb: "A connected multi-post series.",
        fields: [["topic", "Topic", true], ["audience", "Audience"], ["series_length", "Posts", false, "n"], ["series_goal", "Goal"]] },
      outreach_campaign: { label: "Outreach sequence", blurb: "A multi-touch DM/outreach sequence.",
        fields: [["your_offer", "Your offer", true], ["target_role", "Target role", true], ["num_touchpoints", "Touchpoints", false, "n"]] },
      linkedin_brand_audit: { label: "Profile brand audit", blurb: "Score and improve your LinkedIn brand.",
        fields: [["headline", "Headline", true], ["about_section", "About section", true, "a"], ["niche", "Niche"], ["goal", "Goal"]] },
    },
  },
  {
    name: "Graphics",
    tools: {
      social_card: { label: "Social graphic", blurb: "A branded square graphic from a line of text.",
        fields: [["text", "The message / quote", true, "a"], ["theme", "Theme (modern/bold/minimal…)"], ["brand_name", "Brand name"]] },
      ad_creative: { label: "Ad creative", blurb: "Ad copy + matching image per platform.",
        fields: [["product", "Product / service", true], ["offer", "Offer"], ["platform", "Platform"], ["count", "Variations", false, "n"]] },
      infographic: { label: "Infographic", blurb: "An infographic image from your key points.",
        fields: [["topic", "Topic", true], ["content_points", "Key points to visualize", true, "a"], ["infographic_type", "Type"], ["color_scheme", "Color scheme"], ["brand_name", "Brand name"]] },
    },
  },
];

function val(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === "string") return <p style={{ margin: "2px 0", lineHeight: 1.55, fontSize: 13, whiteSpace: "pre-wrap" }}>{v}</p>;
  if (typeof v === "number" || typeof v === "boolean") return <span style={{ fontSize: 13 }}>{String(v)}</span>;
  if (Array.isArray(v))
    return <ul style={{ margin: "2px 0", paddingLeft: 18, fontSize: 13 }}>
      {v.map((x, i) => <li key={i} style={{ marginBottom: 4 }}>{x && typeof x === "object" ? <Blocks data={x} /> : String(x)}</li>)}
    </ul>;
  if (typeof v === "object") return <Blocks data={v} />;
  return <span>{String(v)}</span>;
}
function Blocks({ data }) {
  const entries = Object.entries(data).filter(([k, v]) => !k.startsWith("_") && k !== "image_url" && k !== "html" && v !== null && v !== "");
  return (
    <div>
      {entries.map(([k, v]) => (
        <div key={k} style={{ marginBottom: 8 }}>
          <div style={{ fontWeight: 600, color: "var(--mid)", textTransform: "capitalize", fontSize: 13 }}>{k.replace(/_/g, " ")}</div>
          {val(v)}
        </div>
      ))}
    </div>
  );
}

export default function Studio() {
  const [cat, setCat] = useState(0);
  const [toolKey, setToolKey] = useState(Object.keys(CATEGORIES[0].tools)[0]);
  const [form, setForm] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const tools = CATEGORIES[cat].tools;
  const tool = tools[toolKey];
  const imageUrl = result?.image_url;

  const pickCat = (i) => { setCat(i); const k = Object.keys(CATEGORIES[i].tools)[0]; setToolKey(k); setForm({}); setResult(null); setError(""); };
  const pickTool = (k) => { setToolKey(k); setForm({}); setResult(null); setError(""); };
  const set = (name) => (e) => setForm({ ...form, [name]: e.target.value });

  const run = async (e) => {
    e.preventDefault();
    setError(""); setBusy(true); setResult(null); setCopied(false);
    try {
      for (const f of tool.fields) if (f[2] && !(form[f[0]] || "").trim()) throw new Error(`${f[1]} is required.`);
      const params = {};
      for (const f of tool.fields) {
        const raw = form[f[0]];
        if (raw === undefined || String(raw).trim() === "") continue;
        params[f[0]] = f[3] === "n" ? Number(raw) : raw;
      }
      const res = await studioRun(toolKey, params);
      setResult(res.data);
    } catch (e2) { setError(e2.message); }
    finally { setBusy(false); }
  };

  return (
    <>
      {error && <div className="flash error">{error}</div>}

      <div className="card">
        <h2>Marketing Studio</h2>
        <p className="muted" style={{ marginTop: -6 }}>Reports, email, SEO, LinkedIn formats and graphics — each run uses 1 credit.</p>
        <div className="seg" style={{ marginTop: 4 }}>
          {CATEGORIES.map((c, i) => (
            <button key={c.name} className={cat === i ? "btn-primary" : "btn-secondary"} onClick={() => pickCat(i)}>{c.name}</button>
          ))}
        </div>
        <div className="row" style={{ flexWrap: "wrap", marginTop: 12 }}>
          {Object.entries(tools).map(([k, t]) => (
            <button key={k} className={toolKey === k ? "btn-primary" : "btn-secondary"} onClick={() => pickTool(k)}>{t.label}</button>
          ))}
        </div>
        <p className="muted" style={{ marginTop: 10 }}>{tool.blurb}</p>
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
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn-primary" type="submit" disabled={busy}>{busy ? "Generating…" : "Generate"}</button>
          </div>
        </form>
      </div>

      {result && (
        <div className="card">
          <h2>{tool.label}</h2>
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
          <Blocks data={result} />
        </div>
      )}
    </>
  );
}
