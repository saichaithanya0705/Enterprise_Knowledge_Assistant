const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "eka_access_token";

function storage() {
  return typeof window !== "undefined" ? window.localStorage : null;
}

export const tokenStore = {
  get: () => storage()?.getItem(TOKEN_KEY) || null,
  set: (token) => storage()?.setItem(TOKEN_KEY, token),
  clear: () => storage()?.removeItem(TOKEN_KEY),
};

let unauthorizedHandler = () => {};

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = typeof handler === "function" ? handler : () => {};
  return () => {
    if (unauthorizedHandler === handler) unauthorizedHandler = () => {};
  };
}

function formatErrorDetail(detail, fallback) {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (!item || typeof item !== "object") return String(item);
      const field = Array.isArray(item.loc)
        ? item.loc.filter((part) => !["body", "path", "query"].includes(String(part))).join(".")
        : "";
      const message = typeof item.msg === "string" ? item.msg : "Invalid value";
      return field ? `${field}: ${message}` : message;
    }).filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  if (detail && typeof detail === "object" && typeof detail.msg === "string") {
    return detail.msg;
  }
  return fallback;
}

async function request(path, options = {}) {
  const token = tokenStore.get();
  const headers = options.body instanceof FormData
    ? { ...options.headers }
    : { "Content-Type": "application/json", ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (response.status === 401) {
    tokenStore.clear();
    unauthorizedHandler();
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = formatErrorDetail(data.detail ?? data.message, detail);
    } catch {
      // Keep the HTTP status text when the response is not JSON.
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return null;
  return response.json();
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export const apiClient = {
  tokenStore,
  setUnauthorizedHandler,
  get: (path) => request(path),
  post: (path, body) => request(path, {
    method: "POST",
    body: body instanceof FormData ? body : JSON.stringify(body),
  }),
  patch: (path, body) => request(path, { method: "PATCH", body: JSON.stringify(body) }),
  del: (path) => request(path, { method: "DELETE" }),
};
