import { useRef, useState } from "react";
import { ArrowUpRight } from "lucide-react";

const SUGGESTIONS = [
  { code: "HR", text: "How many days of annual leave do I get?" },
  { code: "IT", text: "How do I reset my password?" },
  { code: "FIN", text: "What expenses can I claim for client meals?" },
  { code: "OPS", text: "What's the equipment stipend for remote work?" },
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
    <div className="relative border-t border-canvas-300 bg-canvas-100/95 px-4 pb-4 pt-3 backdrop-blur sm:px-7 sm:pb-6">
      {showSuggestions && (
        <div className="mx-auto mb-4 max-w-4xl">
          <div className="mb-2 flex items-center gap-3">
            <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-carbon-500">Question starters</p>
            <span className="h-px flex-1 bg-canvas-300" />
          </div>
          <div className="grid gap-px overflow-hidden border border-canvas-300 bg-canvas-300 sm:grid-cols-2 xl:grid-cols-4">
            {SUGGESTIONS.map((suggestion, index) => (
              <button
                key={suggestion.text}
                type="button"
                disabled={disabled}
                aria-label={suggestion.text}
                onClick={() => { if (!disabled) onSend(suggestion.text); }}
                className="group flex min-h-20 items-start gap-3 bg-canvas-50 px-3.5 py-3 text-left transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none"
              >
                <span className="mt-0.5 font-mono text-[9px] text-vermilion-500">{String(index + 1).padStart(2, "0")}</span>
                <span className="min-w-0 flex-1">
                  <span className="block font-mono text-[8px] uppercase tracking-[0.18em] text-carbon-500">{suggestion.code}</span>
                  <span className="mt-1 block text-xs leading-snug text-carbon-900 group-hover:text-vermilion-600">{suggestion.text}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="mx-auto max-w-4xl">
        <label htmlFor="chat-input" className="sr-only">Ask the knowledge base</label>
        <div className="group flex items-end gap-3 border border-carbon-950 bg-canvas-50 p-2 shadow-paper transition-all focus-within:-translate-y-0.5 focus-within:shadow-lift">
          <div className="hidden self-stretch border-r border-canvas-300 px-2 sm:flex sm:items-center">
            <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-carbon-500">Ask</span>
          </div>
          <textarea
            ref={ref}
            id="chat-input"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            placeholder="Ask about policy, access, expenses, or operations..."
            rows={1}
            aria-describedby="chat-input-help"
            aria-keyshortcuts="Enter Shift+Enter"
            className="max-h-32 min-w-0 flex-1 resize-none bg-transparent px-1 py-2.5 text-[15px] leading-relaxed text-carbon-950 placeholder:text-carbon-500 focus:outline-none"
          />
          <button
            type="button"
            aria-label="Send message"
            aria-keyshortcuts="Enter"
            onClick={submit}
            disabled={disabled || !value.trim()}
            className="flex h-11 w-11 shrink-0 items-center justify-center bg-carbon-950 text-canvas-50 transition-all hover:-translate-y-0.5 hover:bg-vermilion-500 active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-25 focus-visible:outline-none"
          >
            <ArrowUpRight size={18} aria-hidden="true" />
          </button>
        </div>
        <div id="chat-input-help" className="mt-2 flex items-center justify-between gap-3 font-mono text-[9px] uppercase tracking-[0.1em] text-carbon-500">
          <span>Evidence status shown on every answer</span>
          <span>Enter to send · Shift + Enter for line break</span>
        </div>
      </div>
    </div>
  );
}
