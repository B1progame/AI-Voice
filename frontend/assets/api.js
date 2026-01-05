// frontend/assets/api.js
function getCookie(name) {
  const parts = document.cookie.split(";").map(s => s.trim());
  for (const p of parts) {
    if (p.startsWith(name + "=")) return decodeURIComponent(p.substring(name.length + 1));
  }
  return null;
}

function csrfHeader() {
  const token = getCookie("csrf_token");
  return token ? { "X-CSRF-Token": token } : {};
}

function formatErrorDetail(detail, status) {
  if (detail == null) return `HTTP ${status}`;

  // FastAPI validation errors: detail is an array
  if (Array.isArray(detail)) {
    // try to build readable message
    const parts = detail.map(e => {
      if (e && typeof e === "object") {
        const loc = Array.isArray(e.loc) ? e.loc.join(".") : "";
        const msg = e.msg || JSON.stringify(e);
        return loc ? `${loc}: ${msg}` : msg;
      }
      return String(e);
    });
    return parts.join(" | ");
  }

  if (typeof detail === "object") {
    try { return JSON.stringify(detail); } catch { return String(detail); }
  }

  return String(detail);
}

async function request(method, url, body) {
  const opts = {
    method,
    credentials: "include",
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...csrfHeader(),
    },
    body: body ? JSON.stringify(body) : undefined,
  };

  const resp = await fetch(url, opts);
  const text = await resp.text();

  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }

  if (!resp.ok) {
    const rawDetail = data?.detail ?? data?.message ?? data?.raw ?? null;
    const detail = formatErrorDetail(rawDetail, resp.status);

    const err = new Error(detail);
    err.status = resp.status;
    err.data = data;
    throw err;
  }

  return data;
}

export const api = {
  me: () => request("GET", "/api/me"),
  register: (email, password) => request("POST", "/api/auth/register", { email, password }),
  login: (email, password) => request("POST", "/api/auth/login", { email, password }),
  logout: () => request("POST", "/api/auth/logout"),

  listConversations: () => request("GET", "/api/conversations"),
  createConversation: (title) => request("POST", "/api/conversations", { title }),
  renameConversation: (id, title) => request("PATCH", `/api/conversations/${id}`, { title }),
  deleteConversation: (id) => request("DELETE", `/api/conversations/${id}`),

  listMessages: (id) => request("GET", `/api/conversations/${id}/messages`),
  createMessage: (id, content) => request("POST", `/api/conversations/${id}/messages`, { content }),

  listPendingUsers: () => request("GET", `/api/admin/users?status=pending`),
  approveUser: (id) => request("POST", `/api/admin/users/${id}/approve`),
  denyUser: (id) => request("POST", `/api/admin/users/${id}/deny`),
};