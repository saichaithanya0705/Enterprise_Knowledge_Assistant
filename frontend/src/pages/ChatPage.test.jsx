import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { ChatPage } from "./ChatPage";
import { deferred } from "../test/deferred";

const mocks = vi.hoisted(() => ({
  getMessages: vi.fn(),
  send: vi.fn(),
  sendFeedback: vi.fn(),
  toast: vi.fn(),
}));

vi.mock("../services/chatService", () => ({ chatService: mocks }));
vi.mock("../context/useToast", () => ({
  useToast: () => ({ push: mocks.toast }),
}));

const trace = {
  original_query: "leave",
  improved_query: "annual leave",
  retrieval_mode: "hybrid",
  embedding_backend: "local_fallback",
  rerank_backend: "local_fallback",
  retrieved_chunks: [{
    chunk_id: "chunk-1",
    filename: "policy.txt",
    section: "Leave",
    bm25_score: 0.8,
    vector_score: 0.4,
    fused_score: 0.6,
    rerank_score: 0.7,
    used_in_context: true,
  }],
  prompt_preview: "[1] policy excerpt",
  llm_backend: "local_fallback",
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getMessages.mockResolvedValue([]);
  mocks.sendFeedback.mockResolvedValue({});
});

test("renders stored debug traces from historical messages after reload", async () => {
  mocks.getMessages.mockResolvedValueOnce([
    { id: "m-1", role: "assistant", content: "You have leave.", sources: [], debug: trace },
  ]);

  render(<ChatPage conversationId="conversation-a" onConversationCreated={vi.fn()} />);

  await screen.findByText("You have leave.");
  fireEvent.click(screen.getByRole("button", { name: "Show RAG trace" }));

  expect(screen.getByText("BM25")).toBeInTheDocument();
  expect(screen.getByText("Vector")).toBeInTheDocument();
  expect(screen.getByText("RRF fused")).toBeInTheDocument();
  expect(screen.getByText("Final rerank")).toBeInTheDocument();
});

test("ignores a stale history response after switching conversations", async () => {
  const oldHistory = deferred();
  const currentHistory = deferred();
  mocks.getMessages.mockImplementation((id) => id === "old" ? oldHistory.promise : currentHistory.promise);

  const { rerender } = render(<ChatPage conversationId="old" onConversationCreated={vi.fn()} />);
  rerender(<ChatPage conversationId="current" onConversationCreated={vi.fn()} />);

  await act(async () => currentHistory.resolve([{ id: "current-message", role: "assistant", content: "Current answer", sources: [] }]));
  await screen.findByText("Current answer");
  await act(async () => oldHistory.resolve([{ id: "old-message", role: "assistant", content: "Stale answer", sources: [] }]));

  await waitFor(() => expect(screen.queryByText("Stale answer")).not.toBeInTheDocument());
  expect(screen.getByText("Current answer")).toBeInTheDocument();
});

test("does not append a stale send response after navigating to another conversation", async () => {
  const sendResponse = deferred();
  mocks.send.mockReturnValue(sendResponse.promise);
  const onConversationCreated = vi.fn();
  const { rerender } = render(<ChatPage conversationId="old" onConversationCreated={onConversationCreated} />);

  await waitFor(() => expect(mocks.getMessages).toHaveBeenCalledWith("old"));
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "old question" } });
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));

  rerender(<ChatPage conversationId="current" onConversationCreated={onConversationCreated} />);
  await act(async () => sendResponse.resolve({
    conversation_id: "old",
    message_id: "old-answer",
    answer: "Old answer should not appear",
    sources: [],
    debug: trace,
  }));

  await waitFor(() => expect(screen.queryByText("Old answer should not appear")).not.toBeInTheDocument());
  expect(onConversationCreated).not.toHaveBeenCalled();
});

test("invalidates a send even when returning to the previous conversation", async () => {
  const sendResponse = deferred();
  mocks.send.mockReturnValue(sendResponse.promise);
  const onConversationCreated = vi.fn();
  const { rerender } = render(<ChatPage conversationId="old" onConversationCreated={onConversationCreated} />);

  await waitFor(() => expect(mocks.getMessages).toHaveBeenCalledWith("old"));
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "old question" } });
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));

  rerender(<ChatPage conversationId="current" onConversationCreated={onConversationCreated} />);
  await waitFor(() => expect(mocks.getMessages).toHaveBeenCalledWith("current"));
  rerender(<ChatPage conversationId="old" onConversationCreated={onConversationCreated} />);
  await waitFor(() => expect(mocks.getMessages).toHaveBeenCalledWith("old"));

  await act(async () => sendResponse.resolve({
    conversation_id: "old",
    message_id: "old-answer",
    answer: "Response from the previous view",
    sources: [],
    debug: trace,
  }));

  expect(screen.queryByText("Response from the previous view")).not.toBeInTheDocument();
  expect(onConversationCreated).not.toHaveBeenCalled();
});

test("clears the open trace when the selected conversation changes", async () => {
  mocks.getMessages.mockResolvedValueOnce([
    { id: "m-1", role: "assistant", content: "Old answer", sources: [], debug: trace },
  ]);
  const { rerender } = render(<ChatPage conversationId="old" onConversationCreated={vi.fn()} />);

  await screen.findByText("Old answer");
  fireEvent.click(screen.getByRole("button", { name: "Show RAG trace" }));
  expect(screen.getByText("RAG pipeline trace")).toBeInTheDocument();

  rerender(<ChatPage conversationId="current" onConversationCreated={vi.fn()} />);
  expect(screen.queryByText("RAG pipeline trace")).not.toBeInTheDocument();
});

test("disables regenerate while a send is active and prevents duplicate requests", async () => {
  const sendResponse = deferred();
  mocks.send.mockReturnValue(sendResponse.promise);
  mocks.getMessages.mockResolvedValueOnce([
    { id: "u-1", role: "user", content: "What is the leave policy?", sources: [] },
    { id: "a-1", role: "assistant", content: "See the policy.", sources: [] },
  ]);

  render(<ChatPage conversationId="conversation-a" onConversationCreated={vi.fn()} />);
  await screen.findByText("See the policy.");

  const regenerate = screen.getByRole("button", { name: "Regenerate answer" });
  fireEvent.click(regenerate);
  expect(mocks.send).toHaveBeenCalledTimes(1);
  expect(regenerate).toBeDisabled();
  fireEvent.click(regenerate);
  expect(mocks.send).toHaveBeenCalledTimes(1);

  await act(async () => sendResponse.resolve({
    conversation_id: "conversation-a",
    message_id: "a-2",
    answer: "A regenerated answer.",
    sources: [],
    debug: trace,
  }));
});

test("does not let stale send A release the send guard owned by newer send B", async () => {
  const sendA = deferred();
  const sendB = deferred();
  mocks.send.mockImplementationOnce(() => sendA.promise).mockImplementationOnce(() => sendB.promise);
  const { rerender } = render(<ChatPage conversationId="conversation-a" onConversationCreated={vi.fn()} />);

  await waitFor(() => expect(mocks.getMessages).toHaveBeenCalledWith("conversation-a"));
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "Question A" } });
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));

  rerender(<ChatPage conversationId="conversation-b" onConversationCreated={vi.fn()} />);
  await waitFor(() => expect(mocks.getMessages).toHaveBeenCalledWith("conversation-b"));
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "Question B" } });
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));
  expect(mocks.send).toHaveBeenCalledTimes(2);

  await act(async () => sendA.resolve({
    conversation_id: "conversation-a",
    message_id: "answer-a",
    answer: "Answer A",
    sources: [],
  }));

  expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();

  await act(async () => sendB.resolve({
    conversation_id: "conversation-b",
    message_id: "answer-b",
    answer: "Answer B",
    sources: [],
  }));
});
