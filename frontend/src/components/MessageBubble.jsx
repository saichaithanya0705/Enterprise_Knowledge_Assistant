import { useState } from "react";
import { Copy, RotateCcw, ThumbsUp, ThumbsDown, Terminal, Check } from "lucide-react";
import { SourceCard } from "./SourceCard";

export function MessageBubble({ message, onFeedback, onShowDebug, onRegenerate }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const copy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (isUser) {
    return (
      <div className="animate-rise-in flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-amber-500 px-4 py-2.5 text-sm text-ink-950 font-medium">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="animate-rise-in flex flex-col gap-2 max-w-[85%]">
      <div className="rounded-2xl rounded-tl-sm border border-ink-600 bg-ink-800 px-4 py-3 text-sm leading-relaxed text-paper-100 whitespace-pre-wrap">
        {message.content}
      </div>

      {message.sources?.length > 0 && (
        <div className="ml-1 grid gap-1.5 pt-1">
          {message.sources.map((s, i) => (
            <SourceCard key={s.chunk_id} index={i + 1} source={s} />
          ))}
        </div>
      )}

      <div className="ml-1 flex items-center gap-3 text-paper-500">
        <button onClick={copy} className="flex items-center gap-1 text-xs hover:text-paper-100 transition-colors">
          {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? "Copied" : "Copy"}
        </button>
        {onRegenerate && (
          <button onClick={onRegenerate} className="flex items-center gap-1 text-xs hover:text-paper-100 transition-colors">
            <RotateCcw size={13} /> Regenerate
          </button>
        )}
        {message.debug && (
          <button onClick={() => onShowDebug(message.debug)} className="flex items-center gap-1 text-xs hover:text-amber-400 transition-colors">
            <Terminal size={13} /> Trace
          </button>
        )}
        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => onFeedback(message.id, 1)} className="hover:text-teal-400 transition-colors">
            <ThumbsUp size={13} />
          </button>
          <button onClick={() => onFeedback(message.id, -1)} className="hover:text-coral-500 transition-colors">
            <ThumbsDown size={13} />
          </button>
        </div>
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm border border-ink-600 bg-ink-800 px-4 py-3 w-fit">
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
