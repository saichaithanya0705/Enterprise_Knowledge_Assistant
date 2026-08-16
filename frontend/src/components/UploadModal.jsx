import { useEffect, useRef, useState } from "react";
import { X, UploadCloud, FileText } from "lucide-react";

const CATEGORIES = ["HR", "IT", "Finance", "General"];

export function UploadModal({ onClose, onUpload }) {
  const [file, setFile] = useState(null);
  const [category, setCategory] = useState("General");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const closeButtonRef = useRef(null);
  const dialogRef = useRef(null);
  const openerRef = useRef(null);
  const busyRef = useRef(busy);
  const onCloseRef = useRef(onClose);

  busyRef.current = busy;
  onCloseRef.current = onClose;

  useEffect(() => {
    openerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus();

    const handleKeyDown = (event) => {
      if (event.key === "Escape" && !busyRef.current) {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = Array.from(dialogRef.current?.querySelectorAll(
        'button:not([disabled]), a[href], input:not([disabled]):not([type="hidden"]):not([type="file"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ) || []);
      if (focusable.length === 0) return;

      const currentIndex = focusable.indexOf(document.activeElement);
      const nextIndex = event.shiftKey
        ? (currentIndex <= 0 ? focusable.length - 1 : currentIndex - 1)
        : (currentIndex === focusable.length - 1 ? 0 : currentIndex + 1);
      event.preventDefault();
      focusable[nextIndex].focus();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      if (openerRef.current?.isConnected) openerRef.current.focus();
    };
  }, []);

  const requestClose = () => {
    if (!busyRef.current) onClose();
  };

  const handleFiles = (files) => {
    if (files?.[0]) {
      setFile(files[0]);
      setError(null);
    }
  };

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await onUpload(file, category);
      onClose();
    } catch (e) {
      setError(e.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 px-4" onClick={requestClose}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-dialog-title"
        aria-describedby="upload-dialog-description"
        className="animate-rise-in w-full max-w-md rounded-2xl border border-ink-600 bg-ink-800 shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-ink-600 px-5 py-4">
          <h2 id="upload-dialog-title" className="font-display text-base text-paper-100">Upload document</h2>
          <button ref={closeButtonRef} type="button" aria-label="Close upload dialog" onClick={requestClose} className="text-paper-500 hover:text-paper-100">
            <X size={16} />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          <p id="upload-dialog-description" className="sr-only">Choose a supported document file and assign it to a knowledge category.</p>
          <button
            type="button"
            aria-label="Choose document file"
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                inputRef.current?.click();
              }
            }}
            className={`flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors ${
              dragging ? "border-amber-500 bg-amber-500/5" : "border-ink-600 hover:border-ink-500"
            }`}
          >
            {file ? (
              <>
                <FileText size={22} className="text-amber-400" />
                <span className="text-sm text-paper-100">{file.name}</span>
                <span className="text-xs text-paper-500">{(file.size / 1024).toFixed(0)} KB - click to change</span>
              </>
            ) : (
              <>
                <UploadCloud size={22} className="text-paper-500" />
                <span className="text-sm text-paper-300">Drag & drop, or click to browse</span>
                <span className="text-xs text-paper-500">PDF, DOCX, TXT, or MD - up to 10MB</span>
              </>
            )}
          </button>
          <input
            ref={inputRef}
            id="upload-file"
            aria-label="Document file"
            type="file"
            accept=".pdf,.docx,.txt,.md"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />

          <div>
            <label className="mb-1.5 block text-xs text-paper-500">Category</label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((c) => (
              <button
                key={c}
                type="button"
                aria-pressed={category === c}
                onClick={() => setCategory(c)}
                className={`min-h-9 rounded-lg border px-3 py-1 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 ${
                    category === c ? "border-amber-500 bg-amber-500/10 text-amber-400" : "border-ink-600 text-paper-300 hover:border-ink-500"
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {error && <p role="alert" className="text-xs text-coral-500">{error}</p>}
        </div>

        <div className="flex justify-end gap-2 border-t border-ink-600 px-5 py-4">
          <button type="button" onClick={requestClose} className="rounded-lg px-3 py-1.5 text-sm text-paper-300 hover:text-paper-100">
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={!file || busy}
            className="rounded-lg bg-amber-500 px-4 py-1.5 text-sm font-medium text-ink-950 hover:bg-amber-400 disabled:opacity-40 transition-colors"
          >
            {busy ? "Ingesting…" : "Upload & ingest"}
          </button>
        </div>
      </div>
    </div>
  );
}
