import { useState } from "react";
import { ChevronDown, FileText } from "lucide-react";

/**
 * Signature element: sources render as small catalog-card citations, echoing
 * how the underlying documents are physical policy handbooks being indexed.
 */
export function SourceCard({ index, source }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative rounded-lg border border-ink-600 bg-ink-800/60 overflow-hidden">
      <div className="absolute -top-2 -left-2 flex h-6 w-6 items-center justify-center rounded-full bg-amber-500 text-[11px] font-mono font-semibold text-ink-950">
        {index}
      </div>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2 px-3 pl-6 py-2.5 text-left hover:bg-ink-700/50 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <FileText size={13} className="text-paper-500 shrink-0" />
          <span className="truncate text-sm text-paper-100">{source.filename}</span>
          {source.section && <span className="hidden sm:inline truncate text-xs text-paper-500">— {source.section}</span>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="font-mono text-[11px] text-teal-400">{(source.similarity * 100).toFixed(0)}%</span>
          <ChevronDown size={14} className={`text-paper-500 transition-transform ${open ? "rotate-180" : ""}`} />
        </div>
      </button>
      {open && (
        <div className="animate-rise-in border-t border-ink-600 px-3 pl-6 py-2.5 text-xs leading-relaxed text-paper-300 font-mono">
          {source.excerpt}…
        </div>
      )}
    </div>
  );
}
