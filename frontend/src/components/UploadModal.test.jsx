import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { UploadModal } from "./UploadModal";

function renderModal(overrides = {}) {
  return render(
    <UploadModal
      onClose={vi.fn()}
      onUpload={vi.fn()}
      {...overrides}
    />,
  );
}

test("focuses the close control when the upload dialog opens", async () => {
  renderModal();

  await waitFor(() => expect(screen.getByRole("button", { name: "Close upload dialog" })).toHaveFocus());
});

test("Escape closes the dialog and restores focus to its opener", async () => {
  const opener = document.createElement("button");
  opener.type = "button";
  opener.textContent = "Open uploader";
  document.body.appendChild(opener);
  opener.focus();
  const onClose = vi.fn();

  const { unmount } = renderModal({ onClose });
  await waitFor(() => expect(screen.getByRole("button", { name: "Close upload dialog" })).toHaveFocus());
  fireEvent.keyDown(document, { key: "Escape" });

  expect(onClose).toHaveBeenCalledTimes(1);
  unmount();
  expect(opener).toHaveFocus();
  document.body.removeChild(opener);
});

test("Escape does not close while an upload is in progress", async () => {
  const upload = new Promise(() => {});
  renderModal({ onUpload: vi.fn(() => upload) });
  const file = new File(["policy"], "policy.txt", { type: "text/plain" });
  fireEvent.change(screen.getByLabelText("Document file"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Upload & ingest" }));

  await waitFor(() => expect(screen.getByRole("button", { name: "Ingesting…" })).toBeDisabled());
  fireEvent.keyDown(document, { key: "Escape" });

  expect(screen.getByRole("dialog")).toBeInTheDocument();
});

test("traps Tab and Shift+Tab inside the upload dialog", async () => {
  renderModal();
  const dialog = screen.getByRole("dialog");
  const close = screen.getByRole("button", { name: "Close upload dialog" });
  const choose = screen.getByRole("button", { name: "Choose document file" });
  const category = screen.getByRole("button", { name: "General" });
  const cancel = screen.getByRole("button", { name: "Cancel" });
  const focusables = [close, choose, ...["HR", "IT", "Finance", "General"].map((name) => screen.getByRole("button", { name })), cancel];

  await waitFor(() => expect(close).toHaveFocus());

  cancel.focus();
  fireEvent.keyDown(cancel, { key: "Tab" });
  expect(close).toHaveFocus();

  close.focus();
  fireEvent.keyDown(close, { key: "Tab", shiftKey: true });
  expect(cancel).toHaveFocus();
  expect(focusables).toHaveLength(7);
  expect(dialog).toBeInTheDocument();
  expect(category).toBeInTheDocument();
});
