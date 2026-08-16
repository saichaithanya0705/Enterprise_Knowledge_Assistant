import { useState, useRef } from "react";
import { X, UploadCloud, FileText } from "lucide-react";

const CATEGORIES = ["HR", "IT", "Finance", "General"];

export function UploadModal({ onClose, onUpload }) {
  const [file, setFile] = useState(null);
  const [category, setCategory] = useState("General");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

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
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 px-4" onClick={onClose}>
      <div
        className="animate-rise-in w-full max-w-md rounded-2xl border border-ink-600 bg-ink-800 shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-ink-600 px-5 py-4">
          <h3 className="font-display text-base text-paper-100">Upload document</h3>
          <button onClick={onClose} className="text-paper-500 hover:text-paper-100">
            <X size={16} />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
            onClick={() => inputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors ${
              dragging ? "border-amber-500 bg-amber-500/5" : "border-ink-600 hover:border-ink-500"
            }`}
          >
            {file ? (
              <>
                <FileText size={22} className="text-amber-400" />
                <p className="text-sm text-paper-100">{file.name}</p>
                <p className="text-xs text-paper-500">{(file.size / 1024).toFixed(0)} KB — click to change</p>
              </>
            ) : (
              <>
                <UploadCloud size={22} className="text-paper-500" />
                <p className="text-sm text-paper-300">Drag & drop, or click to browse</p>
                <p className="text-xs text-paper-500">PDF, DOCX, TXT, or MD — up to 10MB</p>
              </>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs text-paper-500">Category</label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((c) => (
                <button
                  key={c}
                  onClick={() => setCategory(c)}
                  className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                    category === c ? "border-amber-500 bg-amber-500/10 text-amber-400" : "border-ink-600 text-paper-300 hover:border-ink-500"
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-xs text-coral-500">{error}</p>}
        </div>

        <div className="flex justify-end gap-2 border-t border-ink-600 px-5 py-4">
          <button onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-paper-300 hover:text-paper-100">
            Cancel
          </button>
          <button
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
