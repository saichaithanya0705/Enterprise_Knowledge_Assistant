import { useCallback, useState } from "react";
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

  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </ToastCtx.Provider>
  );
}
