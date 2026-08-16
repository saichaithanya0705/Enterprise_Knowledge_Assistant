import { useState } from "react";
import { Copy, RotateCcw, ThumbsUp, ThumbsDown, Terminal, Check, RefreshCcw, AlertCircle } from "lucide-react";
import { SourceCard } from "./SourceCard";

const actionClass = "flex min-h-8 items-center gap-1 rounded-md px-1.5 text-xs text-paper-500 transition-colors hover:bg-ink-700 hover:text-paper-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 disabled:cursor-not-allowed disabled:opacity-40";

export function MessageBubble({ message, onFeedback, onShowDebug, onRegenerate, onRetry, regenerateDisabled = false }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const copy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (message.role === "error") {
    return (
      <div role="alert" className="animate-rise-in flex max-w-[min(85%,42rem)] items-start gap-3 rounded-xl border border-coral-500/40 bg-coral-500/10 px-4 py-3 text-sm text-paper-100">
        <AlertCircle size={17} className="mt-0.5 shrink-0 text-coral-500" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-medium">Unable to answer right now</p>
          <p className="mt-1 break-words text-xs leading-relaxed text-paper-300">{message.content}</p>
          {onRetry && (
            <button type="button" onClick={onRetry} className="mt-3 inline-flex min-h-8 items-center gap-1.5 rounded-md bg-coral-500 px-2.5 text-xs font-semibold text-ink-950 transition-colors hover:bg-coral-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral-500">
              <RefreshCcw size={13} aria-hidden="true" /> Try again
            </button>
          )}
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="animate-rise-in flex justify-end">
        <div className="max-w-[min(75%,42rem)] break-words rounded-2xl rounded-tr-sm bg-amber-500 px-4 py-3 text-sm font-medium leading-relaxed text-ink-950">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <article className="animate-rise-in flex max-w-[min(90%,48rem)] flex-col gap-2">
      <div className="break-words rounded-2xl rounded-tl-sm border border-ink-600 bg-ink-800 px-4 py-3 text-sm leading-relaxed text-paper-100 whitespace-pre-wrap">
        {message.content}
      </div>

      {message.sources?.length > 0 && (
        <div className="ml-1 grid gap-1.5 pt-1">
          <p className="text-[11px] font-medium text-paper-500">Sources</p>
          {message.sources.map((s, i) => (
            <SourceCard key={s.chunk_id} index={i + 1} source={s} />
          ))}
        </div>
      )}

      <div className="ml-1 flex flex-wrap items-center gap-1 text-paper-500">
        <button type="button" aria-label="Copy answer" onClick={copy} className={actionClass}>
          {copied ? <Check size={13} aria-hidden="true" /> : <Copy size={13} aria-hidden="true" />} {copied ? "Copied" : "Copy"}
        </button>
        {onRegenerate && (
          <button type="button" aria-label="Regenerate answer" onClick={onRegenerate} disabled={regenerateDisabled} className={actionClass}>
            <RotateCcw size={13} aria-hidden="true" /> Regenerate
          </button>
        )}
        {message.debug && (
          <button type="button" aria-label="Show RAG trace" onClick={() => onShowDebug(message.debug)} className={`${actionClass} hover:text-amber-400`}>
            <Terminal size={13} aria-hidden="true" /> Trace
          </button>
        )}
        <div className="ml-auto flex items-center gap-1">
          <button type="button" aria-label="Mark answer helpful" onClick={() => onFeedback(message.id, 1)} className={`${actionClass} hover:text-teal-400`}>
            <ThumbsUp size={14} aria-hidden="true" />
          </button>
          <button type="button" aria-label="Mark answer not helpful" onClick={() => onFeedback(message.id, -1)} className={`${actionClass} hover:text-coral-500`}>
            <ThumbsDown size={14} aria-hidden="true" />
          </button>
        </div>
      </div>
    </article>
  );
}

export function TypingIndicator() {
  return (
    <div role="status" aria-live="polite" className="flex w-fit items-center gap-1 rounded-2xl rounded-tl-sm border border-ink-600 bg-ink-800 px-4 py-3">
      <span className="sr-only">Assistant is thinking</span>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="typing-dot h-1.5 w-1.5 rounded-full bg-paper-500"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}
