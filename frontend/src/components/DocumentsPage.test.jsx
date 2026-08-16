import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { DocumentsPage } from "../pages/DocumentsPage";
import { ToastProvider } from "../context/ToastContext";

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  getChunks: vi.fn(),
  remove: vi.fn(),
  upload: vi.fn(),
}));

vi.mock("../services/documentService", () => ({ documentService: mocks }));

function renderPage() {
  return render(
    <ToastProvider>
      <DocumentsPage />
    </ToastProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.list.mockResolvedValue([{ id: "doc-1", filename: "Leave policy.pdf", category: "HR", chunk_count: 1, char_count: 123, status: "ready" }]);
  mocks.getChunks.mockResolvedValue([{ id: "chunk-1", chunk_index: 0, content: "Annual leave details" }]);
  mocks.remove.mockResolvedValue(null);
});

test("keeps document expand and delete controls as sibling buttons", async () => {
  renderPage();

  await screen.findByText("Leave policy.pdf");
  expect(mocks.list).toHaveBeenCalledTimes(1);
  const expand = screen.getByRole("button", { name: "Show chunks for Leave policy.pdf" });
  const deleteButton = screen.getByRole("button", { name: "Delete Leave policy.pdf" });

  expect(expand).not.toContainElement(deleteButton);
  fireEvent.click(expand);
  await screen.findByText("Annual leave details");
  fireEvent.click(deleteButton);
  fireEvent.click(screen.getByRole("button", { name: "Delete document" }));
  expect(mocks.remove).toHaveBeenCalledWith("doc-1");
});

test("keeps document button content phrasing-only", async () => {
  renderPage();

  const expand = await screen.findByRole("button", { name: "Show chunks for Leave policy.pdf" });

  expect(expand.querySelector("div, p")).toBeNull();
});

test("reports chunk preview failures through the toast mechanism", async () => {
  mocks.getChunks.mockRejectedValue(new Error("Chunk preview unavailable"));
  renderPage();

  await screen.findByText("Leave policy.pdf");
  fireEvent.click(screen.getByRole("button", { name: "Show chunks for Leave policy.pdf" }));

  expect((await screen.findAllByText("Chunk preview unavailable")).length).toBeGreaterThanOrEqual(1);
});

test("keeps the upload dialog open and shows an inline retry error after failure", async () => {
  mocks.upload.mockRejectedValueOnce(new Error("Upload failed"));
  renderPage();

  await screen.findByText("Leave policy.pdf");
  fireEvent.click(screen.getByRole("button", { name: "Upload document" }));
  const dropZone = screen.getByRole("button", { name: "Choose document file" });
  fireEvent.keyDown(dropZone, { key: "Enter" });
  const file = new File(["policy"], "policy.txt", { type: "text/plain" });
  fireEvent.change(screen.getByLabelText("Document file"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Upload & ingest" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Upload failed");
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Upload & ingest" })).toBeInTheDocument();
});

test("closes the upload dialog only after a successful upload", async () => {
  mocks.upload.mockResolvedValueOnce({ id: "doc-2" });
  renderPage();

  await screen.findByText("Leave policy.pdf");
  fireEvent.click(screen.getByRole("button", { name: "Upload document" }));
  const file = new File(["policy"], "policy.txt", { type: "text/plain" });
  fireEvent.change(screen.getByLabelText("Document file"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Upload & ingest" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(screen.getByText("policy.txt ingested successfully")).toBeInTheDocument();
});
