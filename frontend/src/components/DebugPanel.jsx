import { X } from "lucide-react";
import { Badge } from "./Badge";

/** Pipeline-rail visualization of the RAG trace: a vertical connected sequence of stages. */
export function DebugPanel({ debug, onClose }) {
  if (!debug) return null;

  const stages = [
    { label: "Original query", value: debug.original_query },
    { label: "Improved query", value: debug.improved_query },
    { label: "Retrieval mode", value: debug.retrieval_mode, tone: "teal" },
    { label: "Embedding backend", value: debug.embedding_backend, tone: debug.embedding_backend === "nvidia" ? "teal" : "amber" },
    { label: "Rerank backend", value: debug.rerank_backend, tone: debug.rerank_backend === "nvidia" ? "teal" : "amber" },
    { label: "Vector store", value: "chromadb", tone: "teal" },
  ];
  return (
    <aside className="animate-rise-in flex h-full w-full max-w-md flex-col border-l border-ink-600 bg-ink-800">
      <div className="flex items-center justify-between border-b border-ink-600 px-4 py-3">
        <h3 className="font-display text-sm text-paper-100">RAG pipeline trace</h3>
        <button onClick={onClose} className="text-paper-500 hover:text-paper-100">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
        {/* Pipeline rail */}
        <ol className="relative space-y-4 border-l border-ink-600 pl-4">
          {stages.map((s, i) => (
            <li key={i} className="relative">
              <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-amber-500" />
              <p className="text-[11px] uppercase tracking-wide text-paper-500">{s.label}</p>
              <p className="mt-0.5 font-mono text-xs text-paper-100 break-words">{s.value}</p>
            </li>
          ))}
        </ol>

        {/* Retrieved candidates with score breakdown */}
        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wide text-paper-500">
            Retrieved candidates ({debug.retrieved_chunks.length})
          </p>
          <div className="space-y-2">
            {debug.retrieved_chunks.map((c) => (
              <div
                key={c.chunk_id}
                className={`rounded-lg border px-3 py-2 ${
                  c.used_in_context ? "border-amber-500/40 bg-amber-500/5" : "border-ink-600 bg-ink-700/30"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-xs text-paper-100">{c.filename}{c.section ? ` — ${c.section}` : ""}</span>
                  {c.used_in_context && <Badge tone="amber">used</Badge>}
                </div>
                <div className="mt-1.5 grid grid-cols-3 gap-2 font-mono text-[10px] text-paper-500">
                  <ScoreBar label="BM25" value={c.bm25_score} />
                  <ScoreBar label="Vector" value={c.vector_score} />
                  <ScoreBar label="Rerank" value={c.fused_score} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wide text-paper-500">Final prompt context (preview)</p>
          <pre className="whitespace-pre-wrap rounded-lg border border-ink-600 bg-ink-950 p-3 font-mono text-[11px] leading-relaxed text-paper-300">
            {debug.prompt_preview}
          </pre>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-wide text-paper-500">LLM backend</span>
          <Badge tone={debug.llm_backend === "key_gateway" ? "teal" : "amber"}>{debug.llm_backend}</Badge>
        </div>
      </div>
    </aside>
  );
}

function ScoreBar({ label, value }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div>
      <div className="flex justify-between"><span>{label}</span><span>{value.toFixed(2)}</span></div>
      <div className="mt-0.5 h-1 w-full overflow-hidden rounded-full bg-ink-600">
        <div className="h-full rounded-full bg-teal-500" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
