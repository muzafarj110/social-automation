// Tiny API client for the LinkedIn Autopilot backend.
// Token is kept in localStorage; all requests go through the Vite /api proxy.

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

async function handle(res) {
  if (res.status === 204) return null;
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* no body */
  }
  if (!res.ok) {
    const msg = body?.detail || body?.error || res.statusText || "Request failed";
    const err = new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    err.status = res.status;
    throw err;
  }
  return body;
}

function authHeaders() {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export async function apiGet(path) {
  return handle(await fetch(`/api${path}`, { headers: { ...authHeaders() } }));
}

export async function apiSend(path, method, data) {
  return handle(
    await fetch(`/api${path}`, {
      method,
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: data === undefined ? undefined : JSON.stringify(data),
    })
  );
}

// --- Auth ---
export async function register(email, password, full_name) {
  const body = await apiSend("/auth/register", "POST", { email, password, full_name });
  setToken(body.access_token);
  return body;
}

export async function login(email, password) {
  // OAuth2 password flow expects form-encoded `username`/`password`.
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const body = await handle(
    await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    })
  );
  setToken(body.access_token);
  return body;
}

export const me = () => apiGet("/auth/me");
export const setHubKey = (hub_api_key) => apiSend("/auth/me/hub-key", "PUT", { hub_api_key });
export const setZernioKey = (zernio_api_key) =>
  apiSend("/auth/me/zernio-key", "PUT", { zernio_api_key });

// --- Accounts ---
export const listAccounts = () => apiGet("/accounts");
export const zernioAvailable = () => apiGet("/accounts/zernio/available");
export const linkAccount = (data) => apiSend("/accounts/link", "POST", data);
export const unlinkAccount = (id) => apiSend(`/accounts/${id}`, "DELETE");

// --- Content / posts ---
export const generatePost = (data) => apiSend("/content/generate/post", "POST", data);
export const createPost = (data) => apiSend("/posts", "POST", data);
export const listPosts = () => apiGet("/posts");
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
