import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import App from "./App";

const mocks = vi.hoisted(() => ({
  listConversations: vi.fn(),
  status: vi.fn(),
}));

vi.mock("./services/chatService", () => ({
  chatService: {
    listConversations: mocks.listConversations,
    deleteConversation: vi.fn(),
  },
}));
vi.mock("./services/systemService", () => ({ systemService: { status: mocks.status } }));

beforeEach(() => {
  vi.clearAllMocks();
  mocks.listConversations.mockResolvedValue([]);
});

test("preserves index lifecycle fields from system status for the sidebar", async () => {
  mocks.status.mockResolvedValue({
    chat_backend: "configured_unverified",
    status: "degraded",
    embedding_backend: "nvidia",
    rerank_backend: "nvidia",
    index_status: "degraded",
    reingest_required: false,
    legacy_collections_present: false,
    historical_generations_present: false,
    pending_cleanup: 2,
    pending_cleanup_count: 2,
    cleanup_action: "POST /api/system/index/reconcile",
    cleanup_metadata_status: "unavailable",
    pending_action: "retry_cleanup",
  });

  render(<App />);

  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/index cleanup|semantic index/i));
  expect(screen.getByTestId("index-status")).toHaveTextContent("degraded");
  expect(screen.getByRole("alert")).toHaveTextContent(/retry_cleanup|cleanup|POST \/api\/system\/index\/reconcile/i);
  expect(screen.getByRole("alert")).toHaveTextContent("POST /api/system/index/reconcile");
  expect(screen.getByRole("alert")).toHaveTextContent(/cleanup metadata is unavailable/i);
});
