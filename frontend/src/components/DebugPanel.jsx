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
    { label: "Retrieval mode", value: debug.retrieval_mode, positive: true },
    { label: "Embedding backend", value: debug.embedding_backend, positive: debug.embedding_backend === "nvidia" },
    { label: "Rerank backend", value: debug.rerank_backend, positive: debug.rerank_backend === "nvidia" },
    { label: "Vector store", value: "chromadb", positive: true },
  ];

  return (
    <aside aria-label="RAG pipeline trace" className="animate-rise-in flex h-full w-full flex-col border-l border-white/10 bg-carbon-950 text-canvas-50">
      <div className="relative flex items-start justify-between border-b border-white/10 px-5 py-5">
        <span className="absolute left-0 top-0 h-full w-1 bg-vermilion-500" />
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-vermilion-400">Operator ledger / 01</p>
          <h2 className="mt-1 font-display text-2xl text-canvas-50">RAG pipeline trace</h2>
          <p className="mt-1 text-xs text-canvas-500">The retrieval path behind this answer.</p>
        </div>
        <button type="button" aria-label="Close RAG trace" onClick={onClose} className="flex h-10 w-10 items-center justify-center border border-white/15 text-canvas-500 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-none">
          <X size={17} aria-hidden="true" />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-6">
        <section aria-labelledby="trace-stages-heading">
          <div className="mb-4 flex items-center gap-3">
            <p id="trace-stages-heading" className="font-mono text-[9px] uppercase tracking-[0.18em] text-canvas-500">Pipeline stages</p>
            <span className="h-px flex-1 bg-white/10" />
          </div>
          <ol className="border-l border-white/15">
            {stages.map((stage, index) => (
              <li key={stage.label} className="relative grid grid-cols-[1.5rem_minmax(0,1fr)] gap-3 pb-5 pl-4 last:pb-0">
                <span className={`absolute -left-1 top-1 h-2 w-2 ${stage.positive ? "bg-moss-400" : "bg-amber-400"}`} />
                <span className="font-display text-lg italic text-canvas-500">{index + 1}</span>
                <div>
                  <p className="font-mono text-[9px] uppercase tracking-[0.12em] text-canvas-500">{stage.label}</p>
                  <p className="mt-1 break-words font-mono text-[11px] leading-5 text-canvas-100">{stage.value ?? "Not available"}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="retrieved-candidates-heading" className="mt-8">
          <div className="mb-3 flex items-center gap-3">
            <p id="retrieved-candidates-heading" className="font-mono text-[9px] uppercase tracking-[0.18em] text-canvas-500">Retrieved candidates</p>
            <span className="h-px flex-1 bg-white/10" />
            <span className="font-mono text-[9px] text-canvas-300">{String(retrievedChunks.length).padStart(2, "0")}</span>
          </div>
          <div className="space-y-px bg-white/10">
            {retrievedChunks.map((chunk, index) => (
              <div key={chunk.chunk_id || chunk.id || `${chunk.filename}-${chunk.section || "chunk"}`} className={`bg-carbon-900 px-3 py-3 ${chunk.used_in_context ? "border-l-2 border-vermilion-500" : "border-l-2 border-transparent"}`}>
                <div className="flex items-start justify-between gap-3">
                  <span className="min-w-0 text-xs text-canvas-100"><span className="mr-2 font-display italic text-vermilion-400">{index + 1}</span>{chunk.filename || "Unknown source"}{chunk.section ? ` / ${chunk.section}` : ""}</span>
                  {chunk.used_in_context && <Badge tone="amber">used</Badge>}
                </div>
                <div className="mt-3 grid grid-cols-4 gap-2 border-t border-white/10 pt-2 font-mono text-[9px] text-canvas-500">
                  <ScoreValue label="BM25" value={chunk.bm25_score} />
                  <ScoreValue label="Vector" value={chunk.vector_score} />
                  <ScoreValue label="RRF fused" value={chunk.fused_score} />
                  <ScoreValue label="Final rerank" value={chunk.rerank_score} />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section aria-labelledby="prompt-preview-heading" className="mt-8">
          <div className="mb-3 flex items-center gap-3">
            <p id="prompt-preview-heading" className="font-mono text-[9px] uppercase tracking-[0.18em] text-canvas-500">Final prompt context</p>
            <span className="h-px flex-1 bg-white/10" />
          </div>
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap border border-white/10 bg-[#10120E] p-4 font-mono text-[10px] leading-5 text-canvas-300">
            {debug.prompt_preview || "No prompt preview available"}
          </pre>
        </section>
      </div>

      <div className="flex items-center justify-between gap-2 border-t border-white/10 bg-carbon-900 px-5 py-4">
        <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-canvas-500">LLM backend</span>
        <Badge tone={debug.llm_backend === "key_gateway" ? "teal" : "amber"}>{debug.llm_backend || "Not available"}</Badge>
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
      <p className="mt-1 text-canvas-100">{displayValue}</p>
    </div>
  );
}
