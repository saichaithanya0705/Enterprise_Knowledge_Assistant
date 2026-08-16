import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, FileText, Trash2, ChevronRight, CheckCircle2, XCircle, Loader2, Search, RefreshCw } from "lucide-react";
import { documentService } from "../services/documentService";
import { UploadModal } from "../components/UploadModal";
import { EmptyState } from "../components/EmptyState";
import { Skeleton } from "../components/Skeleton";
import { Badge } from "../components/Badge";
import { useToast } from "../context/useToast";

const CATEGORIES = ["all", "HR", "IT", "Finance", "General"];
const STATUSES = ["all", "ready", "processing", "failed"];

const STATUS_META = {
  ready: { icon: CheckCircle2, tone: "teal", label: "Ready" },
  processing: { icon: Loader2, tone: "amber", label: "Processing" },
  failed: { icon: XCircle, tone: "coral", label: "Failed" },
};

export function DocumentsPage() {
  const [docs, setDocs] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const [chunks, setChunks] = useState({});
  const [chunkErrors, setChunkErrors] = useState({});
  const [pendingDelete, setPendingDelete] = useState(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState("all");
  const toast = useToast();

  const loadDocuments = useCallback(async ({ reportError = false } = {}) => {
    setLoading(true);
    setLoadError(null);
    try {
      setDocs(await documentService.list());
    } catch (e) {
      const message = e.message || "Unable to load documents";
      setLoadError(message);
      if (reportError) toast.push(message, "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const handleUpload = async (file, selectedCategory) => {
    await documentService.upload(file, selectedCategory);
    toast.push(`${file.name} ingested successfully`);
    await loadDocuments({ reportError: true });
  };

  const confirmDelete = async (doc) => {
    try {
      await documentService.remove(doc.id);
      toast.push(`${doc.filename} removed`);
      setPendingDelete(null);
      await loadDocuments({ reportError: true });
    } catch (e) {
      toast.push(e.message || "Unable to remove document", "error");
    }
  };

  const toggleExpand = async (doc) => {
    if (expanded === doc.id) {
      setExpanded(null);
      return;
    }
    setExpanded(doc.id);
    if (!chunks[doc.id] && !chunkErrors[doc.id]) {
      try {
        const data = await documentService.getChunks(doc.id);
        setChunks((previous) => ({ ...previous, [doc.id]: data }));
      } catch (e) {
        const message = e.message || "Unable to load chunk preview";
        setChunkErrors((previous) => ({ ...previous, [doc.id]: message }));
        toast.push(message, "error");
      }
    }
  };

  const filteredDocs = useMemo(() => {
    if (!docs) return [];
    const normalizedQuery = query.trim().toLowerCase();
    return docs.filter((doc) => {
      const matchesQuery = !normalizedQuery
        || doc.filename.toLowerCase().includes(normalizedQuery)
        || String(doc.category || "").toLowerCase().includes(normalizedQuery);
      const matchesCategory = category === "all" || doc.category === category;
      const matchesStatus = status === "all" || doc.status === status;
      return matchesQuery && matchesCategory && matchesStatus;
    });
  }, [docs, query, category, status]);

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto">
      <header className="border-b border-ink-600 px-4 py-5 sm:px-8 sm:py-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-medium text-amber-400">Knowledge base</p>
            <h1 className="mt-1 font-display text-2xl font-semibold tracking-tight text-paper-100">Documents</h1>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-paper-500">Upload and inspect the documents that ground answers in chat.</p>
          </div>
          <button
            type="button"
            aria-label="Upload document"
            onClick={() => setShowUpload(true)}
            className="flex min-h-10 items-center justify-center gap-1.5 rounded-lg bg-amber-500 px-3.5 py-2 text-sm font-semibold text-ink-950 transition-colors hover:bg-amber-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-900"
          >
            <Plus size={15} aria-hidden="true" /> Upload document
          </button>
        </div>
      </header>

      <div className="flex-1 px-4 py-5 sm:px-8 sm:py-6">
        <div className="mb-5 flex flex-col gap-3 rounded-xl border border-ink-600 bg-ink-800/50 p-3 sm:flex-row sm:items-end">
          <div className="min-w-0 flex-1">
            <label htmlFor="document-search" className="mb-1.5 block text-xs font-medium text-paper-300">Search documents</label>
            <div className="relative">
              <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-paper-500" aria-hidden="true" />
              <input
                id="document-search"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search by file name or category"
                className="min-h-10 w-full rounded-lg border border-ink-600 bg-ink-900 px-3 pl-9 text-sm text-paper-100 placeholder:text-paper-500 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:w-64">
            <FilterSelect label="Category" value={category} onChange={setCategory} options={CATEGORIES} />
            <FilterSelect label="Status" value={status} onChange={setStatus} options={STATUSES} />
          </div>
          <button
            type="button"
            aria-label="Refresh documents"
            onClick={() => loadDocuments({ reportError: true })}
            disabled={loading}
            className="flex min-h-10 items-center justify-center gap-2 rounded-lg border border-ink-600 px-3 text-sm text-paper-300 transition-colors hover:bg-ink-700 hover:text-paper-100 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
          >
            <RefreshCw size={15} className={loading ? "animate-spin" : ""} aria-hidden="true" />
            <span className="sm:hidden">Refresh</span>
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>

        {docs && !loadError && (
          <div className="mb-3 flex items-center justify-between gap-3 text-xs text-paper-500">
            <span>Showing {filteredDocs.length} of {docs.length} documents</span>
            {(query || category !== "all" || status !== "all") && (
              <button type="button" onClick={() => { setQuery(""); setCategory("all"); setStatus("all"); }} className="rounded-md px-2 py-1 text-amber-400 hover:bg-amber-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400">Clear filters</button>
            )}
          </div>
        )}

        {docs === null && loading && (
          <div className="space-y-2" aria-label="Loading documents">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
          </div>
        )}

        {docs === null && loadError && (
          <div role="alert" className="rounded-xl border border-coral-500/40 bg-coral-500/10 p-4">
            <p className="text-sm font-medium text-paper-100">Documents could not be loaded</p>
            <p className="mt-1 text-xs text-paper-300">{loadError}</p>
            <button type="button" onClick={() => loadDocuments({ reportError: true })} className="mt-3 min-h-9 rounded-lg bg-coral-500 px-3 text-xs font-semibold text-ink-950 hover:bg-coral-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral-400">Retry loading documents</button>
          </div>
        )}

        {docs?.length === 0 && !loadError && (
          <EmptyState
            icon={FileText}
            title="No documents yet"
            description="Upload HR, IT, or policy documents to ground the assistant's answers."
            action={<button type="button" onClick={() => setShowUpload(true)} className="mt-2 min-h-10 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-ink-950 hover:bg-amber-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300">Upload your first document</button>}
          />
        )}

        {docs?.length > 0 && filteredDocs.length === 0 && !loadError && (
          <EmptyState
            icon={Search}
            title="No matching documents"
            description="Try a different name, category, or status filter."
            action={<button type="button" onClick={() => { setQuery(""); setCategory("all"); setStatus("all"); }} className="mt-2 min-h-10 rounded-lg border border-ink-600 px-4 py-2 text-sm font-medium text-paper-200 hover:bg-ink-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400">Clear filters</button>}
          />
        )}

        {filteredDocs.length > 0 && (
          <div className="space-y-2">
            {filteredDocs.map((doc) => {
              const meta = STATUS_META[doc.status] || STATUS_META.processing;
              const StatusIcon = meta.icon;
              const isOpen = expanded === doc.id;
              const isPendingDelete = pendingDelete?.id === doc.id;
              return (
                <div key={doc.id} className="overflow-hidden rounded-xl border border-ink-600 bg-ink-800/60">
                  <div className="flex items-stretch gap-1 hover:bg-ink-700/30">
                    <button
                      type="button"
                      aria-expanded={isOpen}
                      aria-controls={`chunks-${doc.id}`}
                      aria-label={`${isOpen ? "Hide" : "Show"} chunks for ${doc.filename}`}
                      onClick={() => toggleExpand(doc)}
                      className="flex min-h-16 min-w-0 flex-1 items-center gap-3 px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-inset"
                    >
                      <FileText size={17} className="shrink-0 text-paper-500" aria-hidden="true" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-paper-100">{doc.filename}</span>
                        <span className="mt-0.5 block truncate text-xs text-paper-500">
                          {doc.category || "General"} · {doc.chunk_count ?? 0} chunks · {Number(doc.char_count || 0).toLocaleString()} chars
                        </span>
                      </span>
                      <span className="hidden text-right text-xs text-paper-500 lg:block">
                        <span className="block">Last indexed</span>
                        <span className="mt-0.5 block text-paper-300">{formatDate(doc.updated_at || doc.created_at)}</span>
                      </span>
                      <Badge tone={meta.tone}>
                        <StatusIcon size={11} className={doc.status === "processing" ? "animate-spin" : ""} aria-hidden="true" /> {meta.label}
                      </Badge>
                      <ChevronRight aria-hidden="true" size={16} className={`shrink-0 text-paper-500 transition-transform ${isOpen ? "rotate-90" : ""}`} />
                    </button>
                    <button
                      type="button"
                      aria-label={`Delete ${doc.filename}`}
                      onClick={() => setPendingDelete(doc)}
                      className="flex min-h-16 w-12 shrink-0 items-center justify-center text-paper-500 transition-colors hover:bg-coral-500/10 hover:text-coral-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral-400"
                    >
                      <Trash2 size={15} aria-hidden="true" />
                    </button>
                  </div>

                  {isPendingDelete && (
                    <div role="alert" className="flex flex-col gap-3 border-t border-coral-500/30 bg-coral-500/10 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                      <p className="text-xs text-paper-200">Delete <span className="font-medium">{doc.filename}</span>? This removes it from the knowledge base.</p>
                      <div className="flex shrink-0 gap-2">
                        <button type="button" onClick={() => setPendingDelete(null)} className="min-h-9 rounded-lg border border-ink-600 px-3 text-xs text-paper-300 hover:bg-ink-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400">Cancel</button>
                        <button type="button" onClick={() => confirmDelete(doc)} className="min-h-9 rounded-lg bg-coral-500 px-3 text-xs font-semibold text-ink-950 hover:bg-coral-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral-400">Delete document</button>
                      </div>
                    </div>
                  )}

                  {isOpen && (
                    <div id={`chunks-${doc.id}`} className="animate-rise-in border-t border-ink-600 bg-ink-950/40 px-4 py-3">
                      {doc.error_message && <p className="mb-2 text-xs text-coral-500">{doc.error_message}</p>}
                      {chunkErrors[doc.id] && <p role="alert" className="mb-2 text-xs text-coral-500">{chunkErrors[doc.id]}</p>}
                      {!chunks[doc.id] && !chunkErrors[doc.id] && <Skeleton className="h-20 w-full" />}
                      <div className="max-h-72 space-y-2 overflow-y-auto">
                        {chunks[doc.id]?.map((chunk) => (
                          <div key={chunk.id} className="rounded-lg border border-ink-600 bg-ink-800 px-3 py-2">
                            <p className="mb-1 font-mono text-[10px] text-paper-500">Chunk {chunk.chunk_index}{chunk.section ? ` / ${chunk.section}` : ""}</p>
                            <p className="line-clamp-3 break-words text-xs leading-relaxed text-paper-300">{chunk.content}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} onUpload={handleUpload} />}
    </div>
  );
}

function FilterSelect({ label, value, onChange, options }) {
  const id = `document-filter-${label.toLowerCase()}`;
  const allLabel = label === "Status" ? "All statuses" : "All categories";
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-xs font-medium text-paper-300">{label}</label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)} className="min-h-10 w-full rounded-lg border border-ink-600 bg-ink-900 px-2.5 text-xs text-paper-200 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20">
        {options.map((option) => <option key={option} value={option}>{option === "all" ? allLabel : option}</option>)}
      </select>
    </div>
  );
}

function formatDate(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date);
}
