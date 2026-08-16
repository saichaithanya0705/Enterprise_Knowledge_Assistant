import { apiClient } from "./apiClient";

const listPayload = (payload) => payload?.items || payload?.data || payload || [];

function withQuery(path, params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ""),
  ).toString();
  return query ? `${path}?${query}` : path;
}

export const adminService = {
  getOverview: () => apiClient.get("/api/admin/analytics/overview"),
  listUsers: async (params) => listPayload(await apiClient.get(withQuery("/api/admin/users", params))),
  updateUser: async (userId, payload) => {
    if (payload.role !== undefined) {
      await apiClient.patch(`/api/admin/users/${userId}/role`, { role: payload.role });
    }
    if (payload.is_active !== undefined) {
      await apiClient.patch(`/api/admin/users/${userId}/active`, { is_active: payload.is_active });
    }
    return payload;
  },
  listConversations: async (params) => listPayload(await apiClient.get(withQuery("/api/admin/conversations", params))),
  getConversation: async (conversation) => ({
    ...(typeof conversation === "object" ? conversation : { id: conversation }),
    messages: await apiClient.get(`/api/admin/conversations/${typeof conversation === "object" ? conversation.id : conversation}/messages`),
  }),
  listRestoreRequests: async (params) => listPayload(await apiClient.get(withQuery("/api/admin/restore-requests", params))),
  resolveRestoreRequest: (requestId, payload) => apiClient.post(`/api/admin/restore-requests/${requestId}/resolve`, payload),
  listAuditLog: async (params) => listPayload(await apiClient.get(withQuery("/api/admin/audit-logs", params))),
};
