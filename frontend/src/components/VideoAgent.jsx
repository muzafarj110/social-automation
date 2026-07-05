import { useEffect, useRef, useState } from "react";
import {
  getVideoChannel, createVideoChannel, updateVideoChannel,
  generateVideo, getVideoJob, listVideos, deleteVideo, createPostFromVideo,
} from "../api.js";

const MUSIC_STYLES = [["calm", "Calm"], ["energetic", "Energetic"]];
const PROGRESS_LABEL = {
  script: "Writing script…", clips: "Fetching stock footage…", audio: "Recording voiceover…",
  render: "Rendering video…", captions: "Generating captions…", thumbnail: "Making thumbnail…",
};
const STATUS_LABEL = {
  queued: "Queued…", generating: "Generating…", completed: "Done", failed: "Failed",
};

function ChannelForm({ initial, onSave, saving }) {
  const [form, setForm] = useState(initial || {
    name: "", handle: "", niche: "", accent_color: "#7c4dff", music_style: "calm",
    tts_voice: "", cache_duration_days: 7,
  });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Video channel</h3>
      <p className="muted" style={{ fontSize: 13 }}>
        One channel per workspace — this shapes every video's voice, look and niche.
      </p>
      <div style={{ display: "grid", gap: 10, maxWidth: 480 }}>
        <label>Channel name
          <input value={form.name} onChange={set("name")} placeholder="AIToolsDaily" />
        </label>
        <label>Handle
          <input value={form.handle} onChange={set("handle")} placeholder="@AIToolsDaily" />
        </label>
        <label>Niche
          <textarea value={form.niche} onChange={set("niche")} rows={2}
            placeholder="AI tools and productivity software" />
        </label>
        <div className="row">
          <label style={{ flex: 1 }}>Accent color
            <input type="color" value={form.accent_color} onChange={set("accent_color")} style={{ width: "100%" }} />
          </label>
          <label style={{ flex: 1 }}>Music style
            <select value={form.music_style} onChange={set("music_style")}>
              {MUSIC_STYLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
        </div>
        <label>Voice (edge-tts voice id, optional)
          <input value={form.tts_voice || ""} onChange={set("tts_voice")} placeholder="en-US-GuyNeural" />
        </label>
        <label>Reuse a cached video for the same topic for how many days?
          <input type="number" min={0} value={form.cache_duration_days}
            onChange={(e) => setForm((f) => ({ ...f, cache_duration_days: Number(e.target.value) }))} />
        </label>
        <button className="btn-primary" disabled={saving || !form.name || !form.handle || !form.niche}
          onClick={() => onSave(form)} style={{ width: "fit-content" }}>
          {saving ? "Saving…" : "Save channel"}
        </button>
      </div>
    </div>
  );
}

function GenerateSection({ channel }) {
  const [topic, setTopic] = useState("");
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const pollRef = useRef(null);

  const clearPoll = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  useEffect(() => () => clearPoll(), []);

  const submit = async () => {
    if (!topic.trim()) return;
    setError(""); setSubmitting(true); setJob(null);
    try {
      const v = await generateVideo(topic.trim());
      setJob(v);
      if (v.status === "queued" || v.status === "generating") {
        pollRef.current = setInterval(async () => {
          try {
            const updated = await getVideoJob(v.id);
            setJob(updated);
            if (updated.status === "completed" || updated.status === "failed") clearPoll();
          } catch { clearPoll(); }
        }, 4000);
      }
    } catch (e) {
      setError(e.message || "Couldn't start generation");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Generate a video</h3>
      <p className="muted" style={{ fontSize: 13 }}>
        Type a topic — {channel.name} will get a short (~60s) and long (~3-4min) cut, both at once.
      </p>
      <div className="row">
        <input style={{ flex: 1 }} placeholder="e.g. 5 free AI tools that replace expensive software"
          value={topic} onChange={(e) => setTopic(e.target.value)}
          disabled={submitting || job?.status === "queued" || job?.status === "generating"} />
        <button className="btn-primary" disabled={submitting || !topic.trim() || job?.status === "queued" || job?.status === "generating"}
          onClick={submit}>
          {submitting ? "Starting…" : "Generate"}
        </button>
      </div>
      {error && <div className="error" role="alert">{error}</div>}

      {job && (
        <div style={{ marginTop: 16, padding: "12px 14px", borderRadius: 8, background: "#f6f7fb" }}
          aria-live="polite">
          <div className="row">
            <span className={`badge ${job.status}`}>{STATUS_LABEL[job.status] || job.status}</span>
            {job.progress_step && <span className="muted">{PROGRESS_LABEL[job.progress_step] || job.progress_step}</span>}
          </div>
          {job.status === "failed" && <div className="error" role="alert" style={{ marginTop: 8 }}>{job.error}</div>}
          {job.status === "completed" && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontWeight: 600 }}>{job.title}</div>
              <div className="row" style={{ marginTop: 8, gap: 12 }}>
                {job.thumbnail_url && <img src={job.thumbnail_url} alt={`Thumbnail for ${job.title || "generated video"}`} style={{ width: 90, borderRadius: 6 }} />}
                <div className="muted" style={{ fontSize: 12 }}>
                  {job.video_short_url && <div>✓ Short cut ready</div>}
                  {job.video_long_url && <div>✓ Long cut ready</div>}
                  <div style={{ marginTop: 4 }}>Find it in the Gallery tab to attach it to a post.</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function VideoCard({ video, accounts, onChange }) {
  const [accountId, setAccountId] = useState("");
  const [variant, setVariant] = useState(video.video_short_url ? "short" : "long");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const createPost = async () => {
    if (!accountId) return;
    setBusy(true); setError("");
    try {
      await createPostFromVideo(video.id, Number(accountId), variant);
      onChange();
    } catch (e) {
      setError(e.message || "Couldn't create post");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm("Delete this video? This cannot be undone.")) return;
    setBusy(true);
    try { await deleteVideo(video.id); onChange(); }
    catch (e) { setError(e.message); setBusy(false); }
  };

  return (
    <div className="card">
      <div className="row">
        <span className={`badge ${video.status}`}>{STATUS_LABEL[video.status] || video.status}</span>
        <span className="muted" style={{ fontSize: 12 }}>{new Date(video.requested_at).toLocaleDateString()}</span>
      </div>
      <div style={{ fontWeight: 600, marginTop: 6 }}>{video.title || video.topic}</div>
      {video.error && <div className="error" role="alert" style={{ fontSize: 12 }}>{video.error}</div>}
      {error && <div className="error" role="alert" style={{ fontSize: 12 }}>{error}</div>}

      {video.status === "completed" && (
        <>
          {video.thumbnail_url && (
            <img src={video.thumbnail_url} alt={`Thumbnail for ${video.title || video.topic}`} style={{ width: "100%", borderRadius: 8, marginTop: 8 }} />
          )}
          <div className="row" style={{ marginTop: 10, flexWrap: "wrap", gap: 8 }}>
            {video.video_short_url && <a href={video.video_short_url} target="_blank" rel="noreferrer" className="btn-ghost">View short</a>}
            {video.video_long_url && <a href={video.video_long_url} target="_blank" rel="noreferrer" className="btn-ghost">View long</a>}
          </div>

          {(video.short_post_id || video.long_post_id) ? (
            <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>
              Already added to Posts{video.short_post_id && video.long_post_id ? " (both cuts)" : ""}.
            </div>
          ) : (
            <div style={{ marginTop: 10, padding: "10px 12px", borderRadius: 8, background: "#f6f7fb" }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Create a post from this video</div>
              <div className="row" style={{ flexWrap: "wrap" }}>
                <select value={variant} onChange={(e) => setVariant(e.target.value)}>
                  {video.video_short_url && <option value="short">Short cut</option>}
                  {video.video_long_url && <option value="long">Long cut</option>}
                </select>
                <select value={accountId} onChange={(e) => setAccountId(e.target.value)} style={{ flex: 1 }}>
                  <option value="">Choose an account…</option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>{a.platform} — {a.display_name || a.platform}</option>
                  ))}
                </select>
                <button className="btn-secondary" disabled={busy || !accountId} onClick={createPost}>
                  {busy ? "…" : "Create post"}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      <div className="row" style={{ marginTop: 10 }}>
        <div className="spacer" />
        <button className="btn-ghost" disabled={busy} onClick={remove}>Delete</button>
      </div>
    </div>
  );
}

function GallerySection({ accounts }) {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try { setVideos(await listVideos()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  if (loading) return <div className="empty">Loading…</div>;
  return (
    <>
      {error && <div className="error" role="alert">{error}</div>}
      {videos.length === 0 ? (
        <div className="empty">No videos yet. Generate one to get started.</div>
      ) : (
        <div className="masonry">
          {videos.map((v) => <VideoCard key={v.id} video={v} accounts={accounts} onChange={load} />)}
        </div>
      )}
    </>
  );
}

export default function VideoAgent({ accounts = [] }) {
  const [channel, setChannel] = useState(null);
  const [channelLoaded, setChannelLoaded] = useState(false);
  const [section, setSection] = useState("generate");
  const [savingChannel, setSavingChannel] = useState(false);
  const [error, setError] = useState("");

  const loadChannel = async () => {
    try { setChannel(await getVideoChannel()); }
    catch { setChannel(null); }
    finally { setChannelLoaded(true); }
  };
  useEffect(() => { loadChannel(); }, []);

  useEffect(() => {
    if (channelLoaded) setSection(channel ? "generate" : "settings");
  }, [channelLoaded]); // eslint-disable-line

  const saveChannel = async (form) => {
    setSavingChannel(true); setError("");
    try {
      const saved = channel ? await updateVideoChannel(form) : await createVideoChannel(form);
      setChannel(saved);
      setSection("generate");
    } catch (e) {
      setError(e.message || "Couldn't save channel");
    } finally {
      setSavingChannel(false);
    }
  };

  if (!channelLoaded) return <div className="empty">Loading…</div>;

  return (
    <div>
      {error && <div className="error" role="alert" style={{ marginBottom: 12 }}>{error}</div>}
      <div className="filter-row" style={{ marginBottom: 16 }}>
        <button className={`filter-chip ${section === "generate" ? "active" : ""}`}
          disabled={!channel} onClick={() => setSection("generate")}>Generate</button>
        <button className={`filter-chip ${section === "gallery" ? "active" : ""}`}
          disabled={!channel} onClick={() => setSection("gallery")}>Gallery</button>
        <button className={`filter-chip ${section === "settings" ? "active" : ""}`}
          onClick={() => setSection("settings")}>Settings</button>
      </div>

      {section === "settings" && (
        <ChannelForm initial={channel} onSave={saveChannel} saving={savingChannel} />
      )}
      {section === "generate" && channel && <GenerateSection channel={channel} />}
      {section === "gallery" && channel && <GallerySection accounts={accounts} />}
    </div>
  );
}
