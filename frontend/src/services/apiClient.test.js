import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { apiClient, setUnauthorizedHandler, tokenStore } from "./apiClient";

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  setUnauthorizedHandler(null);
  vi.unstubAllGlobals();
});

test("attaches the stored bearer token without overriding FormData headers", async () => {
  tokenStore.set("signed-token");
  fetch.mockResolvedValue({ ok: true, status: 204 });

  await apiClient.post("/api/documents", new FormData());

  expect(fetch).toHaveBeenCalledWith(
    expect.stringMatching(/\/api\/documents$/),
    expect.objectContaining({
      method: "POST",
      headers: { Authorization: "Bearer signed-token" },
    }),
  );
});

test("clears the token and notifies auth state after a 401", async () => {
  const unauthorized = vi.fn();
  tokenStore.set("expired-token");
  setUnauthorizedHandler(unauthorized);
  fetch.mockResolvedValue({
    ok: false,
    status: 401,
    statusText: "Unauthorized",
    json: async () => ({ detail: "Expired" }),
  });

  await expect(apiClient.get("/api/auth/me")).rejects.toMatchObject({ status: 401 });
  expect(tokenStore.get()).toBeNull();
  expect(unauthorized).toHaveBeenCalledTimes(1);
});

test("formats FastAPI validation details as a readable error message", async () => {
  fetch.mockResolvedValue({
    ok: false,
    status: 422,
    statusText: "Unprocessable Entity",
    json: async () => ({
      detail: [
        {
          loc: ["body", "email"],
          msg: "value is not a valid email address",
        },
      ],
    }),
  });

  await expect(apiClient.post("/api/auth/login", {
    email: "invalid",
    password: "Example!123",
  })).rejects.toMatchObject({
    status: 422,
    message: "email: value is not a valid email address",
  });
});
