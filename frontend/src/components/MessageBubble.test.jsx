import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import { MessageBubble } from "./MessageBubble";

const originalClipboard = navigator.clipboard;

afterEach(() => {
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: originalClipboard });
});

test("does not claim clipboard success when the browser rejects the write", async () => {
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: vi.fn().mockRejectedValue(new Error("Permission denied")) },
  });

  render(
    <MessageBubble
      message={{ id: "answer-1", role: "assistant", content: "Policy answer", sources: [], grounded: false }}
      onFeedback={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Copy answer" }));

  expect(await screen.findByText("Copy unavailable")).toBeInTheDocument();
});
