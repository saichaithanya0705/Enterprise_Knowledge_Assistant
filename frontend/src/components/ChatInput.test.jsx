import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ChatInput } from "./ChatInput";

test("disables suggestions while a chat send is in progress", () => {
  const onSend = vi.fn();
  render(<ChatInput onSend={onSend} disabled showSuggestions />);

  const suggestion = screen.getByRole("button", { name: "How many days of annual leave do I get?" });
  expect(suggestion).toBeDisabled();
  fireEvent.click(suggestion);
  expect(onSend).not.toHaveBeenCalled();
});
