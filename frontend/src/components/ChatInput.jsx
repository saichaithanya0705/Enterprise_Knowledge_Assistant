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
        <div className="mb-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => onSend(s)}
              className="rounded-full border border-ink-600 bg-ink-800 px-3 py-1.5 text-xs text-paper-300 hover:border-amber-500/50 hover:text-amber-400 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <div className="flex items-end gap-2 rounded-2xl border border-ink-600 bg-ink-800 p-2 focus-within:border-amber-500/50 transition-colors">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Ask about leave, expenses, IT access, remote work…"
          rows={1}
          className="max-h-32 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-paper-100 placeholder:text-paper-500 focus:outline-none"
        />
        <button
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-500 text-ink-950 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-amber-400 transition-colors"
        >
          <ArrowUp size={16} />
        </button>
      </div>
    </div>
  );
}
