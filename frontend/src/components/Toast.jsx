import { useEffect } from "react";
import { CheckCircle2, XCircle, X } from "lucide-react";

export function Toast({ toast, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(() => onDismiss(toast.id), 4000);
    return () => clearTimeout(t);
  }, [toast.id, onDismiss]);

  const isError = toast.tone === "error";
  return (
    <div className="animate-rise-in flex items-center gap-2 rounded-xl border border-ink-600 bg-ink-800 px-4 py-3 shadow-card">
      {isError ? <XCircle size={16} className="text-coral-500 shrink-0" /> : <CheckCircle2 size={16} className="text-teal-400 shrink-0" />}
      <p className="text-sm text-paper-100">{toast.message}</p>
      <button onClick={() => onDismiss(toast.id)} className="ml-2 text-paper-500 hover:text-paper-100">
        <X size={14} />
      </button>
    </div>
  );
}

export function ToastStack({ toasts, onDismiss }) {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80">
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
