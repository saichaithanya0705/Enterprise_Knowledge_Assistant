import { useEffect, useRef, useState } from "react";
import { AlertCircle, Check, Copy, RefreshCcw, RotateCcw, Terminal, ThumbsDown, ThumbsUp } from "lucide-react";
import { SourceCard } from "./SourceCard";

const actionClass = "inline-flex min-h-8 items-center gap-1.5 border-b border-transparent px-1 text-[11px] text-carbon-500 transition-colors hover:border-carbon-500 hover:text-carbon-950 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-40";

export function MessageBubble({ message, onFeedback, onShowDebug, onRegenerate, onRetry, regenerateDisabled = false }) {
  const [copyState, setCopyState] = useState("idle");
  const copyResetRef = useRef(null);
  const isUser = message.role === "user";
  const isGrounded = message.grounded === true
    || (message.grounded === undefined && Boolean(message.sources?.length));

  useEffect(() => () => window.clearTimeout(copyResetRef.current), []);

  const copy = async () => {
    window.clearTimeout(copyResetRef.current);
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard API unavailable");
      await navigator.clipboard.writeText(message.content);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
    copyResetRef.current = window.setTimeout(() => setCopyState("idle"), 1800);
  };

  if (message.role === "error") {
    return (
      <div role="alert" className="animate-rise-in border-l-4 border-vermilion-500 bg-[#F8E9E3] px-5 py-4 text-carbon-950">
        <div className="flex items-start gap-3">
          <AlertCircle size={18} className="mt-0.5 shrink-0 text-vermilion-600" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="font-display text-lg">The desk could not answer</p>
            <p className="mt-1 break-words text-sm leading-relaxed text-carbon-500">{message.content}</p>
            {onRetry && (
              <button type="button" onClick={onRetry} className="mt-3 inline-flex min-h-9 items-center gap-2 bg-vermilion-500 px-3 text-xs font-semibold text-white transition-colors hover:bg-vermilion-600 focus-visible:outline-none">
                <RefreshCcw size={13} aria-hidden="true" /> Try again
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <section className="animate-rise-in ml-auto w-full max-w-[42rem] border-r-4 border-vermilion-500 bg-canvas-200/70 px-5 py-4 text-right">
        <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-vermilion-600">Your inquiry</p>
        <p className="mt-2 break-words font-display text-xl leading-snug text-carbon-950 sm:text-2xl">{message.content}</p>
      </section>
    );
  }

  return (
    <article className="animate-rise-in w-full">
      <div className="mb-2 flex items-center gap-3">
        <span className={`font-mono text-[9px] uppercase tracking-[0.2em] ${isGrounded ? "text-moss-500" : "text-vermilion-600"}`}>{isGrounded ? "Grounded response" : "No cited evidence"}</span>
        <span className="h-px flex-1 bg-canvas-300" />
        <span className="font-mono text-[9px] text-carbon-500">{String(message.sources?.length || 0).padStart(2, "0")} sources</span>
      </div>

      <div className="relative border border-canvas-300 bg-canvas-50 px-5 py-5 shadow-paper sm:px-7 sm:py-6">
        <span className={`absolute -left-px top-5 h-12 w-[3px] ${isGrounded ? "bg-moss-500" : "bg-vermilion-500"}`} aria-hidden="true" />
        <div className="whitespace-pre-wrap break-words text-[15px] leading-7 text-carbon-900 sm:text-base">
          {message.content}
        </div>
      </div>

      {message.sources?.length > 0 && (
        <section className="mt-3 border-l border-canvas-300 pl-3 xl:hidden" aria-label="Answer sources">
          <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Evidence cited</p>
          <div className="space-y-px border border-canvas-300 bg-canvas-300">
            {message.sources.map((source, index) => (
              <SourceCard key={source.chunk_id || `${source.filename}-${index}`} index={index + 1} source={source} />
            ))}
          </div>
        </section>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-canvas-300 pt-2">
        <button type="button" aria-label="Copy answer" onClick={copy} className={actionClass}>
          {copyState === "copied" ? <Check size={13} aria-hidden="true" /> : <Copy size={13} aria-hidden="true" />}
          {copyState === "copied" ? "Copied" : copyState === "failed" ? "Copy unavailable" : "Copy"}
        </button>
        {onRegenerate && (
          <button type="button" aria-label="Regenerate answer" onClick={onRegenerate} disabled={regenerateDisabled} className={actionClass}>
            <RotateCcw size={13} aria-hidden="true" /> Regenerate
          </button>
        )}
        {message.debug && (
          <button type="button" aria-label="Show RAG trace" onClick={() => onShowDebug(message.debug)} className={`${actionClass} hover:border-vermilion-500 hover:text-vermilion-600`}>
            <Terminal size={13} aria-hidden="true" /> Inspect trace
          </button>
        )}
        <span className="mx-1 h-3 w-px bg-canvas-300" aria-hidden="true" />
        <button type="button" aria-label="Helpful answer" onClick={() => onFeedback(message.id, 1)} className={actionClass}><ThumbsUp size={13} aria-hidden="true" /> Useful</button>
        <button type="button" aria-label="Not helpful answer" onClick={() => onFeedback(message.id, -1)} className={actionClass}><ThumbsDown size={13} aria-hidden="true" /> Needs work</button>
      </div>
    </article>
  );
}

export function TypingIndicator() {
  return (
    <div role="status" aria-live="polite" className="animate-rise-in flex items-center gap-4 border-l-4 border-moss-500 bg-canvas-50 px-5 py-4 shadow-paper">
      <span className="sr-only">Assistant is thinking</span>
      <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Searching the archive</span>
      <span className="flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((index) => <span key={index} className="typing-dot h-1.5 w-1.5 bg-moss-500" style={{ animationDelay: `${index * 0.16}s` }} />)}
      </span>
    </div>
  );
}
