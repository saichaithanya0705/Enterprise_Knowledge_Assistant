import { useState } from "react";
import { ChevronDown, FileText } from "lucide-react";

export function SourceCard({ index, source }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="overflow-hidden rounded-lg border border-ink-600 bg-ink-800/60">
      <button
        type="button"
        aria-expanded={open}
        aria-label={`${open ? "Hide" : "Show"} source excerpt from ${source.filename}`}
        onClick={() => setOpen((current) => !current)}
        className="flex min-h-11 w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition-colors hover:bg-ink-700/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-inset"
      >
        <span className="flex min-w-0 items-center gap-2">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-amber-500/15 font-mono text-[11px] font-semibold text-amber-400">{index}</span>
          <FileText size={14} className="shrink-0 text-paper-500" aria-hidden="true" />
          <span className="min-w-0 truncate text-sm text-paper-100">{source.filename}</span>
          {source.section && <span className="hidden truncate text-xs text-paper-500 sm:inline">{source.section}</span>}
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <span className="text-[11px] text-paper-500">Source {index}</span>
          <ChevronDown size={14} className={`text-paper-500 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden="true" />
        </span>
      </button>
      {open && (
        <div className="animate-rise-in border-t border-ink-600 px-4 py-3 text-xs leading-relaxed text-paper-300">
          {source.excerpt || "No excerpt available."}
        </div>
      )}
    </div>
  );
}
