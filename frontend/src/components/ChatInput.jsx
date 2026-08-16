import { useState, useRef } from "react";
import { ArrowUp } from "lucide-react";

const SUGGESTIONS = [
  "How many days of annual leave do I get?",
  "How do I reset my password?",
  "What expenses can I claim for client meals?",
  "What's the equipment stipend for remote work?",
];

export function ChatInput({ onSend, disabled, showSuggestions }) {
  const [value, setValue] = useState("");
  const ref = useRef(null);

  const submit = () => {
    if (!value.trim() || disabled) return;
    onSend(value.trim());
    setValue("");
    ref.current?.focus();
  };

  return (
    <div className="border-t border-ink-600 bg-ink-900 px-4 py-3 sm:px-6 sm:py-4">
      {showSuggestions && (
        <div className="mx-auto mb-3 max-w-3xl">
          <p className="mb-2 text-[11px] font-medium text-paper-500">Try a question</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                disabled={disabled}
                aria-label={s}
                onClick={() => { if (!disabled) onSend(s); }}
                className="min-h-9 rounded-lg border border-ink-600 bg-ink-800 px-3 py-1.5 text-left text-xs text-paper-300 transition-colors hover:border-amber-500/50 hover:bg-ink-700 hover:text-amber-400 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="mx-auto max-w-3xl">
        <label htmlFor="chat-input" className="sr-only">Ask the knowledge base</label>
        <div className="flex items-end gap-2 rounded-2xl border border-ink-600 bg-ink-800 p-2 transition-colors focus-within:border-amber-500/70 focus-within:ring-1 focus-within:ring-amber-500/30">
          <textarea
            ref={ref}
            id="chat-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Ask about leave, expenses, IT access, remote work..."
            rows={1}
            aria-describedby="chat-input-help"
            aria-keyshortcuts="Enter Shift+Enter"
            className="max-h-32 min-w-0 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-relaxed text-paper-100 placeholder:text-paper-500 focus:outline-none"
          />
          <button
            type="button"
            aria-label="Send message"
            aria-keyshortcuts="Enter"
            onClick={submit}
            disabled={disabled || !value.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500 text-ink-950 transition-colors hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-800"
          >
            <ArrowUp size={17} aria-hidden="true" />
          </button>
        </div>
        <p id="chat-input-help" className="mt-2 text-center text-[11px] text-paper-500">Enter to send. Shift + Enter for a new line.</p>
      </div>
    </div>
  );
}
