import { useEffect, useRef, useState } from "react";
import { FileText, UploadCloud, X } from "lucide-react";
import { DOCUMENT_ACCEPT, DOCUMENT_EXTENSIONS, MAX_DOCUMENT_BYTES, validateDocumentFile } from "./documentUploadPolicy";

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
    const selectedFile = files?.[0];
    if (!selectedFile) return;
    const validationError = validateDocumentFile(selectedFile);
    setFile(validationError ? null : selectedFile);
    setError(validationError);
  };

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await onUpload(file, category);
      onClose();
    } catch (uploadError) {
      setError(uploadError.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-carbon-950/65 px-4 py-8 backdrop-blur-[3px]" onClick={requestClose}>
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="upload-dialog-title" aria-describedby="upload-dialog-description" className="paper-noise relative max-h-full w-full max-w-2xl overflow-y-auto border border-carbon-950 bg-canvas-50 shadow-lift" onClick={(event) => event.stopPropagation()}>
        <div className="relative flex items-start justify-between border-b border-carbon-950 bg-carbon-950 px-6 py-5 text-canvas-50">
          <span className="absolute left-0 top-0 h-full w-1 bg-vermilion-500" />
          <div>
            <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-vermilion-400">Archive intake / New record</p>
            <h2 id="upload-dialog-title" className="mt-1 font-display text-3xl">Upload document</h2>
          </div>
          <button ref={closeButtonRef} type="button" aria-label="Close upload dialog" onClick={requestClose} className="flex h-10 w-10 items-center justify-center border border-white/15 text-canvas-500 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-none">
            <X size={17} aria-hidden="true" />
          </button>
        </div>

        <div className="grid gap-6 px-6 py-6 md:grid-cols-[minmax(0,1fr)_13rem]">
          <p id="upload-dialog-description" className="sr-only">Choose a supported document file and assign it to a knowledge category.</p>
          <button
            type="button"
            aria-label="Choose document file"
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); handleFiles(event.dataTransfer.files); }}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                inputRef.current?.click();
              }
            }}
            className={`flex min-h-56 cursor-pointer flex-col items-center justify-center border-2 border-dashed px-6 py-8 text-center transition-all ${dragging ? "border-vermilion-500 bg-[#F8E9E3]" : "border-canvas-300 bg-canvas-100 hover:border-carbon-950 hover:bg-white"}`}
          >
            {file ? (
              <>
                <FileText size={28} strokeWidth={1.4} className="text-vermilion-500" aria-hidden="true" />
                <span className="mt-4 break-all font-display text-xl text-carbon-950">{file.name}</span>
                <span className="mt-2 font-mono text-[9px] uppercase tracking-[0.14em] text-carbon-500">{(file.size / 1024).toFixed(0)} KB · click to replace</span>
              </>
            ) : (
              <>
                <UploadCloud size={30} strokeWidth={1.3} className="text-vermilion-500" aria-hidden="true" />
                <span className="mt-4 font-display text-2xl italic text-carbon-950">Drop a file into the archive</span>
                <span className="mt-2 text-xs text-carbon-500">or click to browse your computer</span>
                <span className="mt-6 border-t border-canvas-300 pt-3 font-mono text-[9px] uppercase tracking-[0.14em] text-carbon-500">{DOCUMENT_EXTENSIONS.join(" / ").toUpperCase()} / {MAX_DOCUMENT_BYTES / 1024 / 1024}MB max</span>
              </>
            )}
          </button>
          <input ref={inputRef} id="upload-file" aria-label="Document file" type="file" accept={DOCUMENT_ACCEPT} className="hidden" onChange={(event) => handleFiles(event.target.files)} />

          <div>
            <label className="mb-3 block font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Category</label>
            <div className="space-y-px bg-canvas-300">
              {CATEGORIES.map((item, index) => (
                <button key={item} type="button" aria-label={item} aria-pressed={category === item} onClick={() => setCategory(item)} className={`flex min-h-11 w-full items-center justify-between px-3 text-left text-xs transition-colors focus-visible:outline-none ${category === item ? "bg-carbon-950 text-canvas-50" : "bg-canvas-100 text-carbon-900 hover:bg-white"}`}>
                  <span>{item}</span><span className={`font-display text-lg italic ${category === item ? "text-vermilion-400" : "text-carbon-500"}`}>{index + 1}</span>
                </button>
              ))}
            </div>
            <p className="mt-4 text-xs leading-5 text-carbon-500">Categories keep retrieval filters legible as the archive grows.</p>
          </div>

          {error && <p role="alert" className="border-l-4 border-vermilion-500 bg-[#F8E9E3] px-3 py-2 text-xs text-vermilion-600 md:col-span-2">{error}</p>}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-carbon-950 px-6 py-4">
          <p className="hidden font-mono text-[9px] uppercase tracking-[0.12em] text-carbon-500 sm:block">Files are parsed and indexed after upload</p>
          <div className="ml-auto flex gap-2">
            <button type="button" onClick={requestClose} className="min-h-10 border border-carbon-950 px-4 text-sm text-carbon-950 transition-colors hover:bg-canvas-200 focus-visible:outline-none">Cancel</button>
            <button type="button" onClick={submit} disabled={!file || busy} className="min-h-10 bg-vermilion-500 px-5 text-sm font-semibold text-white transition-colors hover:bg-vermilion-600 disabled:cursor-not-allowed disabled:opacity-35 focus-visible:outline-none">
              {busy ? "Ingesting…" : "Upload & ingest"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
