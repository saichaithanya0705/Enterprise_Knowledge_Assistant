import { apiClient } from "./apiClient";

export const tokenStore = apiClient.tokenStore || {};

const readFromStore = () => {
  if (typeof tokenStore.get === "function") return tokenStore.get();
  if (typeof tokenStore.getToken === "function") return tokenStore.getToken();
  return null;
};

const writeToStore = (token) => {
  if (!token) return;
  if (typeof tokenStore.set === "function") tokenStore.set(token);
  else if (typeof tokenStore.setToken === "function") tokenStore.setToken(token);
};

export const clearStoredToken = () => {
  if (typeof tokenStore.clear === "function") tokenStore.clear();
  else if (typeof tokenStore.remove === "function") tokenStore.remove();
  else if (typeof tokenStore.removeToken === "function") tokenStore.removeToken();
};

export const hasStoredToken = () => Boolean(readFromStore());

export function normalizeUser(payload) {
  const user = payload?.user || payload?.data?.user || payload?.data || payload;
  if (!user || typeof user !== "object") return null;
  return {
    ...user,
    name: user.name || user.full_name || user.display_name || user.email || "Workspace member",
    role: user.role || (user.is_admin ? "admin" : "user"),
  };
}

function persistResponse(response) {
  const token = response?.access_token || response?.token || response?.data?.access_token || response?.data?.token;
  writeToStore(token);
  return { token, user: normalizeUser(response) };
}

export const authService = {
  register: async (payload) => persistResponse(await apiClient.post("/api/auth/register", payload)),
  login: async (payload) => persistResponse(await apiClient.post("/api/auth/login", payload)),
  me: async () => normalizeUser(await apiClient.get("/api/auth/me")),
  updateProfile: async (payload) => normalizeUser(await apiClient.patch("/api/auth/me", payload)),
  changePassword: (payload) => apiClient.post("/api/auth/change-password", payload),
  logout: async () => {
    clearStoredToken();
  },
};
