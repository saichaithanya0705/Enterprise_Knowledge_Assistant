import { apiClient } from "./apiClient";

export const systemService = {
  status: () => apiClient.get("/api/system/status"),
};
