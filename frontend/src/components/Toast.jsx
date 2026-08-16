import { useEffect } from "react";
import { CheckCircle2, XCircle, X } from "lucide-react";

export function Toast({ toast, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(() => onDismiss(toast.id), 4000);
    return () => clearTimeout(t);
  }, [toast.id, onDismiss]);

  const isError = toast.tone === "error";
  return (
    <div role="status" aria-live={isError ? "assertive" : "polite"} aria-atomic="true" className="animate-rise-in flex items-center gap-2 rounded-xl border border-ink-600 bg-ink-800 px-4 py-3 shadow-card">
      {isError ? <XCircle size={16} className="text-coral-500 shrink-0" /> : <CheckCircle2 size={16} className="text-teal-400 shrink-0" />}
      <p className="text-sm text-paper-100">{toast.message}</p>
      <button type="button" aria-label="Dismiss notification" onClick={() => onDismiss(toast.id)} className="ml-2 text-paper-500 hover:text-paper-100">
        <X size={14} />
      </button>
    </div>
  );
}

export function ToastStack({ toasts, onDismiss }) {
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[calc(100vw-2rem)] max-w-sm flex-col gap-2 sm:w-80">
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto">
          <Toast toast={t} onDismiss={onDismiss} />
        </div>
      ))}
    </div>
  );
}
