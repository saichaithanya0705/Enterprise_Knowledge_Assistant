import { render, screen } from "@testing-library/react";
import { DebugPanel } from "./DebugPanel";

test("keeps older traces readable when stages or scores are missing", () => {
  render(
    <DebugPanel
      debug={{
        original_query: "leave",
        improved_query: "leave",
        retrieval_mode: "hybrid",
        retrieved_chunks: [{
          id: "legacy-chunk",
          filename: "policy.txt",
          bm25_score: "0.5",
          vector_score: null,
          fused_score: "0.3",
        }],
      }}
      onClose={() => {}}
    />,
  );

  expect(screen.getByText("policy.txt")).toBeInTheDocument();
  expect(screen.getByText("BM25")).toBeInTheDocument();
  expect(screen.getByText("RRF fused")).toBeInTheDocument();
  expect(screen.getByText("Final rerank")).toBeInTheDocument();
  expect(screen.getAllByText("Not available").length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("LLM backend").parentElement).toHaveTextContent("Not available");
  expect(screen.getByText("No prompt preview available")).toBeInTheDocument();
});
