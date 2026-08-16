import { useState } from "react";
import { ChevronDown } from "lucide-react";

export function SourceCard({ index, source }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-canvas-50">
      <button
        type="button"
        aria-expanded={open}
        aria-label={`${open ? "Hide" : "Show"} source excerpt from ${source.filename}`}
        onClick={() => setOpen((current) => !current)}
        className="group flex min-h-12 w-full items-center gap-3 px-3.5 py-3 text-left transition-colors hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-vermilion-500"
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center border border-carbon-950 font-display text-sm italic text-carbon-950">{index}</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold text-carbon-950">{source.filename}</span>
          <span className="mt-0.5 block truncate font-mono text-[9px] uppercase tracking-[0.12em] text-carbon-500">{source.section || `Source ${index}`}</span>
        </span>
        <ChevronDown size={14} className={`shrink-0 text-carbon-500 transition-transform duration-200 ${open ? "rotate-180" : ""}`} aria-hidden="true" />
      </button>
      {open && (
        <div className="animate-rise-in border-t border-canvas-300 bg-canvas-100 px-4 py-3 text-xs leading-6 text-carbon-700">
          <span className="mr-1 font-display text-xl leading-none text-vermilion-500" aria-hidden="true">“</span>
          {source.excerpt || "No excerpt available."}
        </div>
      )}
    </div>
  );
}
