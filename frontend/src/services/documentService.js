import { apiClient } from "./apiClient";

export const documentService = {
  list: () => apiClient.get("/api/documents"),
  upload: (file, category) => {
    const form = new FormData();
    form.append("file", file);
    form.append("category", category || "General");
    return apiClient.post("/api/documents", form);
  },
  getChunks: (docId) => apiClient.get(`/api/documents/${docId}/chunks`),
  remove: (docId) => apiClient.del(`/api/documents/${docId}`),
};
