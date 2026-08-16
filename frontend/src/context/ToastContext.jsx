import { useCallback, useMemo, useState } from "react";
import { ToastStack } from "../components/Toast";
import { ToastCtx } from "./toastContextValue";

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((message, tone = "success") => {
    const id = crypto.randomUUID();
    setToasts((t) => [...t, { id, message, tone }]);
  }, []);

  const dismiss = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const contextValue = useMemo(() => ({ push }), [push]);

  return (
    <ToastCtx.Provider value={contextValue}>
      {children}
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </ToastCtx.Provider>
  );
}
