import { apiClient } from "./apiClient";

const listPayload = (payload) => payload?.items || payload?.data || payload || [];

export const restoreRequestService = {
  listDeletedConversations: async () => listPayload(await apiClient.get("/api/conversations/deleted")),
  listMine: async () => listPayload(await apiClient.get("/api/conversations/restore-requests/mine")),
  requestRestore: (conversationId, reason) => apiClient.post(`/api/conversations/${conversationId}/restore-requests`, { reason }),
};
