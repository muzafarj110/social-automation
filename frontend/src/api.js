import axios from "axios";

const TOKEN_KEY = "autopilot_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}
export function logout() {
  setToken(null);
}

// Axios instance — all requests go through the Vite /api proxy
const http = axios.create({ baseURL: "/api" });

// Attach Bearer token on every request
http.interceptors.request.use((config) => {
  const t = getToken();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// On 401: clear token and signal the app to show login
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && getToken()) {
      setToken(null);
      window.dispatchEvent(new Event("auth:expired"));
    }
    // Normalise error message so callers can do e.message
    const detail = err.response?.data?.detail || err.response?.data?.error;
    if (detail) err.message = typeof detail === "string" ? detail : JSON.stringify(detail);
    return Promise.reject(err);
  }
);

export async function apiGet(path) {
  const r = await http.get(path);
  return r.data ?? null;
}

export async function apiSend(path, method, data) {
  const lower = method.toLowerCase();
  let r;
  if (lower === "delete") {
    r = await http.delete(path);
  } else if (data !== undefined) {
    r = await http[lower](path, data);
  } else {
    r = await http[lower](path);
  }
  return r.data ?? null;
}

// --- Auth ---
export async function register(email, password, full_name) {
  const body = await apiSend("/auth/register", "POST", { email, password, full_name });
  if (body?.access_token && !body?.verification_required) setToken(body.access_token);
  return body;
}

export async function verifyEmail(token) {
  const body = await apiSend("/auth/verify-email", "POST", { token });
  setToken(body.access_token);
  return body;
}
export const resendVerification = (email) => apiSend("/auth/resend-verification", "POST", { email });

export async function login(email, password) {
  // OAuth2 password flow expects form-encoded username/password
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const r = await http.post("/auth/login", form.toString(), {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  setToken(r.data.access_token);
  return r.data;
}

export const forgotPassword = (email) => apiSend("/auth/forgot-password", "POST", { email });
export async function resetPassword(token, new_password) {
  const body = await apiSend("/auth/reset-password", "POST", { token, new_password });
  setToken(body.access_token);
  return body;
}

export const me = () => apiGet("/auth/me");
export const setProfile = (profile_type) => apiSend("/auth/me/profile", "PUT", { profile_type });
export const setHubKey = (hub_api_key) => apiSend("/auth/me/hub-key", "PUT", { hub_api_key });
export const setAutomation = (paused) => apiSend("/auth/me/automation", "PUT", { paused });
export const changePassword = (current_password, new_password) =>
  apiSend("/auth/me/password", "PUT", { current_password, new_password });
export const setZernioKey = (zernio_api_key) =>
  apiSend("/auth/me/zernio-key", "PUT", { zernio_api_key });

// --- Accounts ---
export const listAccounts = () => apiGet("/accounts");
export const zernioAvailable = () => apiGet("/accounts/zernio/available");
export const connectUrl = (platform, redirect_url) =>
  apiSend("/accounts/connect-url", "POST", { platform, redirect_url });
export const linkAccount = (data) => apiSend("/accounts/link", "POST", data);
export const unlinkAccount = (id) => apiSend(`/accounts/${id}`, "DELETE");

// --- Content / posts ---
export const generatePost = (data) => apiSend("/content/generate/post", "POST", data);
export const qaCheck = (data) => apiSend("/content/qa", "POST", data);
export const optimizeContent = (data) => apiSend("/content/optimize", "POST", data);
export const generateInfographic = (data) => apiSend("/content/infographic", "POST", data);
export const getUsage = () => apiGet("/content/usage");
export const studioRun = (tool, params) => apiSend("/content/studio", "POST", { tool, params });
export const createPost = (data) => apiSend("/posts", "POST", data);
export const listPosts = () => apiGet("/posts");
export const listCampaignPosts = (campaignId) => apiGet(`/posts?campaign_id=${campaignId}`);
export const updatePost = (id, data) => apiSend(`/posts/${id}`, "PATCH", data);
export const syncPosts = () => apiSend("/posts/sync", "POST", {});
export const getPostInfographic = (id) => apiGet(`/posts/${id}/infographic`);
export const publishPost = (id) => apiSend(`/posts/${id}/publish`, "POST", {});
export const schedulePost = (id, scheduled_for, timezone) =>
  apiSend(`/posts/${id}/schedule`, "POST", { scheduled_for, timezone });
export const deletePost = (id) => apiSend(`/posts/${id}`, "DELETE");

// --- Approval inbox ---
export const generateApproval = (data) => apiSend("/inbox/generate", "POST", data);
export const listInbox = (status = "pending") =>
  apiGet(`/inbox?status=${encodeURIComponent(status)}`);
export const editApproval = (id, draft_text) =>
  apiSend(`/inbox/${id}`, "PATCH", { draft_text });
export const approveApproval = (id) => apiSend(`/inbox/${id}/approve`, "POST", {});
export const rejectApproval = (id) => apiSend(`/inbox/${id}/reject`, "POST", {});

// --- Campaigns (autopilot) ---
export const listCampaigns = () => apiGet("/campaigns");
export const createCampaign = (data) => apiSend("/campaigns", "POST", data);
export const updateCampaign = (id, data) => apiSend(`/campaigns/${id}`, "PATCH", data);
export const deleteCampaign = (id) => apiSend(`/campaigns/${id}`, "DELETE");
export const runCampaign = (id) => apiSend(`/campaigns/${id}/run`, "POST", {});

// --- Brand (strategy brain) ---
export const getBrand = () => apiGet("/brand");
export const saveBrand = (data) => apiSend("/brand", "PUT", data);
export const brandGenerate = (tool, params) => apiSend("/brand/generate", "POST", { tool, params });

// --- Profile Studio ---
export const profileOptimize = (data) => apiSend("/profile-studio/optimize", "POST", data);
export const profileHeadlines = (data) => apiSend("/profile-studio/headlines", "POST", data);
export const profileFeatured = (data) => apiSend("/profile-studio/featured", "POST", data);
export const profileRecommendation = (data) => apiSend("/profile-studio/recommendation", "POST", data);

// --- Leads (CRM-lite) ---
export const listLeads = () => apiGet("/leads");
export const createLead = (data) => apiSend("/leads", "POST", data);
export const updateLead = (id, data) => apiSend(`/leads/${id}`, "PATCH", data);
export const deleteLead = (id) => apiSend(`/leads/${id}`, "DELETE");
export const draftOutreach = (id) => apiSend(`/leads/${id}/draft-outreach`, "POST", {});

// --- Opportunities ---
export const listOpportunities = () => apiGet("/opportunities");

// --- Proactive feed ---
export const listProactiveItems = () => apiGet("/proactive");
export const generateProactiveItem = () => apiSend("/proactive/generate", "POST", {});
export const dismissProactiveItem = (id) => apiSend(`/proactive/${id}/dismiss`, "POST", {});

// --- Social Listening agent ---
export const listTopics = () => apiGet("/listening");
export const createTopic = (data) => apiSend("/listening", "POST", data);
export const updateTopic = (id, data) => apiSend(`/listening/${id}`, "PATCH", data);
export const deleteTopic = (id) => apiSend(`/listening/${id}`, "DELETE");
export const scanTopic = (id) => apiSend(`/listening/${id}/scan`, "POST", {});

// --- SEO + GEO agent ---
export const listSeoProjects = () => apiGet("/seo");
export const createSeoProject = (data) => apiSend("/seo", "POST", data);
export const updateSeoProject = (id, data) => apiSend(`/seo/${id}`, "PATCH", data);
export const deleteSeoProject = (id) => apiSend(`/seo/${id}`, "DELETE");
export const analyzeSeoProject = (id) => apiSend(`/seo/${id}/analyze`, "POST", {});

// --- Competitor Strategy agent ---
export const listCompetitors = () => apiGet("/competitors");
export const createCompetitor = (data) => apiSend("/competitors", "POST", data);
export const updateCompetitor = (id, data) => apiSend(`/competitors/${id}`, "PATCH", data);
export const deleteCompetitor = (id) => apiSend(`/competitors/${id}`, "DELETE");
export const analyzeCompetitor = (id) => apiSend(`/competitors/${id}/analyze`, "POST", {});

// --- Clients (agency multi-client workspaces) ---
export const listClients = () => apiGet("/clients");
export const createClient = (name) => apiSend("/clients", "POST", { name });
export const activateClient = (id) => apiSend(`/clients/${id}/activate`, "POST", {});
export const deactivateClient = () => apiSend("/clients/deactivate", "POST", {});

// --- Content Team (agentic weekly cycle) ---
export const teamPlan = (count = 3, directive = "") => apiSend("/team/plan", "POST", { count, directive: directive || undefined });
export const teamRun = (data) => apiSend("/team/run", "POST", data);
export const listTeamRuns = () => apiGet("/team/runs");
export const getTeamRun = (id) => apiGet(`/team/runs/${id}`);
export const approveTeamRun = (id) => apiSend(`/team/runs/${id}/approve`, "POST", {});

// --- Channel connections (WhatsApp + Telegram) ---
export const getConnections = () => apiGet("/connections");
export const connectWhatsApp = (data) => apiSend("/connections/whatsapp", "POST", data);
export const disconnectWhatsApp = () => apiSend("/connections/whatsapp", "DELETE");
export const toggleWhatsAppAutoPost = () => apiSend("/connections/whatsapp/toggle", "PATCH", {});
export const sendWhatsApp = (data) => apiSend("/connections/whatsapp/send", "POST", data);
export const getWhatsAppAgentSettings = () => apiGet("/connections/whatsapp/agent");
export const updateWhatsAppAgentSettings = (data) => apiSend("/connections/whatsapp/agent", "PATCH", data);
export const listWhatsAppFlagged = () => apiGet("/connections/whatsapp/flagged");
export const dismissWhatsAppFlagged = (messageId) => apiSend(`/connections/whatsapp/flagged/${messageId}/dismiss`, "POST", {});
export const connectTelegram = (data) => apiSend("/connections/telegram", "POST", data);
export const disconnectTelegram = () => apiSend("/connections/telegram", "DELETE");
export const toggleTelegramAutoPost = () => apiSend("/connections/telegram/toggle", "PATCH", {});
export const sendTelegram = (data) => apiSend("/connections/telegram/send", "POST", data);

// --- Billing ---
export const getBilling = () => apiGet("/billing");
export const startCheckout = (price_id) => apiSend("/billing/checkout", "POST", { price_id });
export const openBillingPortal = () => apiSend("/billing/portal", "POST", {});

// --- Media upload ---
export async function uploadMedia(file) {
  const form = new FormData();
  form.append("file", file);
  const r = await http.post("/media/upload", form);
  return r.data;
}

// --- Admin ---
export const adminListUsers = () => apiGet("/admin/users");
export const adminFeatures = () => apiGet("/admin/features");
export const adminUpdateUser = (id, data) => apiSend(`/admin/users/${id}`, "PATCH", data);
export const adminDeleteUser = (id) => apiSend(`/admin/users/${id}`, "DELETE");
export const adminResetLink = (id) => apiSend(`/admin/users/${id}/reset-link`, "POST", {});
export const adminEmailConfig = () => apiGet("/admin/email-config");
export const adminTestEmail = (to, category) =>
  apiSend("/admin/test-email", "POST", { ...(to ? { to } : {}), ...(category ? { category } : {}) });

// --- Video agent (Faceless Video Pipeline) ---
export const getVideoChannel = () => apiGet("/videos/channel");
export const createVideoChannel = (data) => apiSend("/videos/channel", "POST", data);
export const updateVideoChannel = (data) => apiSend("/videos/channel", "PATCH", data);
export const generateVideo = (topic) => apiSend("/videos/generate", "POST", { topic });
export const getVideoJob = (id) => apiGet(`/videos/jobs/${id}`);
export const listVideos = () => apiGet("/videos");
export const deleteVideo = (id) => apiSend(`/videos/${id}`, "DELETE");
export const createPostFromVideo = (id, account_id, variant) =>
  apiSend(`/videos/${id}/create-post`, "POST", { account_id, variant });

// --- Analytics ---
export const zernioMetrics = () => apiGet("/analytics/zernio");
export const getInsights = (data) => apiSend("/analytics/insights", "POST", data);
export const analyzeViral = (data) => apiSend("/analytics/viral", "POST", data);
