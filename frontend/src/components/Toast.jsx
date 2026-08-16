import { useEffect } from "react";
import { CheckCircle2, XCircle, X } from "lucide-react";

export function Toast({ toast, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(() => onDismiss(toast.id), 4000);
    return () => clearTimeout(t);
  }, [toast.id, onDismiss]);

  const isError = toast.tone === "error";
  return (
    <div role="status" aria-live={isError ? "assertive" : "polite"} aria-atomic="true" className={`animate-rise-in flex items-center gap-3 border border-carbon-950 border-l-4 bg-canvas-50 px-4 py-3 shadow-lift ${isError ? "border-l-vermilion-500" : "border-l-moss-500"}`}>
      {isError ? <XCircle size={16} className="shrink-0 text-vermilion-600" /> : <CheckCircle2 size={16} className="shrink-0 text-moss-500" />}
      <p className="flex-1 text-sm text-carbon-950">{toast.message}</p>
      <button type="button" aria-label="Dismiss notification" onClick={() => onDismiss(toast.id)} className="ml-2 flex h-8 w-8 items-center justify-center text-carbon-500 hover:bg-canvas-200 hover:text-carbon-950">
        <X size={14} />
      </button>
    </div>
  );
}

export function ToastStack({ toasts, onDismiss }) {
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[calc(100vw-2rem)] max-w-sm flex-col gap-2 sm:w-96">
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto">
          <Toast toast={t} onDismiss={onDismiss} />
        </div>
      ))}
    </div>
  );
}
