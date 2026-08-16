import { X } from "lucide-react";
import { Badge } from "./Badge";

/** Operator-only view of the retrieval trace behind an answer. */
export function DebugPanel({ debug, onClose }) {
  if (!debug) return null;
  const retrievedChunks = Array.isArray(debug.retrieved_chunks)
    ? debug.retrieved_chunks
    : Array.isArray(debug.retrievedChunks) ? debug.retrievedChunks : [];

  const stages = [
    { label: "Original query", value: debug.original_query },
    { label: "Improved query", value: debug.improved_query },
    { label: "Retrieval mode", value: debug.retrieval_mode, tone: "teal" },
    { label: "Embedding backend", value: debug.embedding_backend, tone: debug.embedding_backend === "nvidia" ? "teal" : "amber" },
    { label: "Rerank backend", value: debug.rerank_backend, tone: debug.rerank_backend === "nvidia" ? "teal" : "amber" },
    { label: "Vector store", value: "chromadb", tone: "teal" },
  ];
  return (
    <aside aria-label="RAG pipeline trace" className="animate-rise-in flex h-full w-full flex-col border-l border-ink-600 bg-ink-800 shadow-card">
      <div className="flex items-center justify-between border-b border-ink-600 px-4 py-3">
        <div>
          <p className="text-[11px] font-medium text-amber-400">Operator view</p>
          <h2 className="font-display text-sm text-paper-100">RAG pipeline trace</h2>
        </div>
        <button type="button" aria-label="Close RAG trace" onClick={onClose} className="flex h-9 w-9 items-center justify-center rounded-lg text-paper-500 hover:bg-ink-700 hover:text-paper-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400">
          <X size={16} aria-hidden="true" />
        </button>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto px-4 py-4">
        <ol className="relative space-y-4 border-l border-ink-600 pl-4">
          {stages.map((stage, index) => (
            <li key={index} className="relative">
              <span className={`absolute -left-[21px] top-1 h-2 w-2 rounded-full ${stage.tone === "teal" ? "bg-teal-500" : "bg-amber-500"}`} />
              <p className="text-[11px] font-medium text-paper-500">{stage.label}</p>
              <p className="mt-0.5 break-words font-mono text-xs text-paper-100">{stage.value ?? "Not available"}</p>
            </li>
          ))}
        </ol>

        <section aria-labelledby="retrieved-candidates-heading">
          <p id="retrieved-candidates-heading" className="mb-2 text-[11px] font-medium text-paper-500">
            Retrieved candidates <span className="font-mono text-paper-300">({retrievedChunks.length})</span>
          </p>
          <div className="space-y-2">
            {retrievedChunks.map((chunk) => (
              <div
                key={chunk.chunk_id || chunk.id || `${chunk.filename}-${chunk.section || "chunk"}`}
                className={`rounded-lg border px-3 py-2 ${
                  chunk.used_in_context ? "border-amber-500/40 bg-amber-500/5" : "border-ink-600 bg-ink-700/30"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-xs text-paper-100">{chunk.filename || "Unknown source"}{chunk.section ? ` / ${chunk.section}` : ""}</span>
                  {chunk.used_in_context && <Badge tone="amber">used</Badge>}
                </div>
                <div className="mt-2 grid grid-cols-4 gap-2 font-mono text-[10px] text-paper-500">
                  <ScoreValue label="BM25" value={chunk.bm25_score} />
                  <ScoreValue label="Vector" value={chunk.vector_score} />
                  <ScoreValue label="RRF fused" value={chunk.fused_score} />
                  <ScoreValue label="Final rerank" value={chunk.rerank_score} />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section aria-labelledby="prompt-preview-heading">
          <p id="prompt-preview-heading" className="mb-2 text-[11px] font-medium text-paper-500">Final prompt context</p>
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border border-ink-600 bg-ink-950 p-3 font-mono text-[11px] leading-relaxed text-paper-300">
            {debug.prompt_preview || "No prompt preview available"}
          </pre>
        </section>

        <div className="flex items-center justify-between gap-2 rounded-lg border border-ink-600 bg-ink-900/60 px-3 py-2">
          <span className="text-[11px] font-medium text-paper-500">LLM backend</span>
          <Badge tone={debug.llm_backend === "key_gateway" ? "teal" : "amber"}>{debug.llm_backend || "Not available"}</Badge>
        </div>
      </div>
    </aside>
  );
}

function ScoreValue({ label, value }) {
  const parsedValue = value === null || value === undefined || value === ""
    ? null
    : typeof value === "number" ? value : Number(value);
  const displayValue = Number.isFinite(parsedValue) ? parsedValue.toFixed(2) : "Not available";
  return (
    <div className="min-w-0">
      <p className="truncate">{label}</p>
      <p className="mt-0.5 text-paper-300">{displayValue}</p>
    </div>
  );
}
