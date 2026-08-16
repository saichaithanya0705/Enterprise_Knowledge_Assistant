import { apiClient } from "./apiClient";

export const chatService = {
  send: (message, conversationId) =>
    apiClient.post("/api/chat", { message, conversation_id: conversationId || null }),
  listConversations: () => apiClient.get("/api/conversations"),
  getMessages: (conversationId) => apiClient.get(`/api/conversations/${conversationId}/messages`),
  deleteConversation: (conversationId) => apiClient.del(`/api/conversations/${conversationId}`),
  sendFeedback: (messageId, rating) => apiClient.post("/api/feedback", { message_id: messageId, rating }),
};
