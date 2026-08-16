import { render, screen } from "@testing-library/react";
import { SourceCard } from "./SourceCard";

test("keeps source toggle button content phrasing-only", () => {
  render(
    <SourceCard
      index={1}
      source={{ filename: "policy.txt", section: "Leave", similarity: 0.8, excerpt: "Annual leave" }}
    />,
  );

  const toggle = screen.getByRole("button", { name: "Show source excerpt from policy.txt" });
  expect(toggle.querySelector("div, p")).toBeNull();
});
