import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, ChevronRight, FileText, Loader2, Plus, RefreshCw, Search, Trash2, XCircle } from "lucide-react";
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
    } catch (error) {
      const message = error.message || "Unable to load documents";
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
    } catch (error) {
      toast.push(error.message || "Unable to remove document", "error");
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
      } catch (error) {
        const message = error.message || "Unable to load chunk preview";
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

  const metrics = useMemo(() => ({
    documents: docs?.length || 0,
    chunks: docs?.reduce((total, doc) => total + Number(doc.chunk_count || 0), 0) || 0,
    ready: docs?.filter((doc) => doc.status === "ready").length || 0,
  }), [docs]);

  return (
    <div className="h-full overflow-y-auto bg-canvas-100">
      <div className="mx-auto w-full max-w-[92rem] px-4 pb-12 pt-7 sm:px-7 sm:pt-10 lg:px-10">
        <header className="grid gap-8 border-b border-carbon-950 pb-8 lg:grid-cols-[minmax(0,1fr)_25rem] lg:items-end">
          <div>
            <div className="mb-4 flex items-center gap-3">
              <span className="font-mono text-[9px] uppercase tracking-[0.24em] text-vermilion-600">Archive / Document index</span>
              <span className="h-px w-16 bg-vermilion-500" />
            </div>
            <h1 className="text-balance font-display text-[clamp(3.8rem,8vw,7.5rem)] leading-[0.78] tracking-[-0.055em] text-carbon-950">The<br /><span className="italic text-vermilion-500">library.</span></h1>
            <p className="mt-6 max-w-2xl text-pretty text-sm leading-7 text-carbon-500 sm:text-base">Manage the source material behind every answer. Open a record to inspect how it was divided for retrieval.</p>
          </div>

          <div className="grid grid-cols-3 border border-carbon-950 bg-canvas-50">
            <Metric label="Documents" value={metrics.documents} />
            <Metric label="Chunks" value={metrics.chunks} />
            <Metric label="Ready" value={metrics.ready} />
            <button type="button" aria-label="Upload document" onClick={() => setShowUpload(true)} className="col-span-3 flex min-h-12 items-center justify-between border-t border-carbon-950 bg-carbon-950 px-4 text-sm font-semibold text-canvas-50 transition-all hover:bg-vermilion-500 focus-visible:outline-none">
              Add to the archive <Plus size={17} aria-hidden="true" />
            </button>
          </div>
        </header>

        <section aria-label="Document filters" className="my-7 grid gap-3 border-y border-canvas-300 py-4 md:grid-cols-[minmax(16rem,1fr)_10rem_10rem_auto] md:items-end">
          <div>
            <label htmlFor="document-search" className="mb-2 block font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Search the index</label>
            <div className="relative">
              <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-carbon-500" aria-hidden="true" />
              <input id="document-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="File name or category" className="min-h-11 w-full border border-carbon-950 bg-canvas-50 px-3 pl-9 text-sm text-carbon-950 placeholder:text-carbon-500 focus:outline-none focus:ring-2 focus:ring-vermilion-500" />
            </div>
          </div>
          <FilterSelect label="Category" value={category} onChange={setCategory} options={CATEGORIES} />
          <FilterSelect label="Status" value={status} onChange={setStatus} options={STATUSES} />
          <button type="button" aria-label="Refresh documents" onClick={() => loadDocuments({ reportError: true })} disabled={loading} className="flex min-h-11 items-center justify-center gap-2 border border-carbon-950 px-4 text-xs font-semibold text-carbon-950 transition-colors hover:bg-carbon-950 hover:text-canvas-50 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} aria-hidden="true" /> Refresh
          </button>
        </section>

        {docs && !loadError && (
          <div className="mb-3 flex items-center justify-between gap-3 font-mono text-[9px] uppercase tracking-[0.14em] text-carbon-500">
            <span>Showing {filteredDocs.length} of {docs.length} records</span>
            {(query || category !== "all" || status !== "all") && (
              <button type="button" onClick={() => { setQuery(""); setCategory("all"); setStatus("all"); }} className="text-vermilion-600 underline decoration-vermilion-400 underline-offset-4 focus-visible:outline-none">Clear filters</button>
            )}
          </div>
        )}

        {docs === null && loading && (
          <div className="space-y-px border-y border-canvas-300" aria-label="Loading documents">
            {[1, 2, 3].map((index) => <Skeleton key={index} className="h-20 w-full rounded-none bg-canvas-200" />)}
          </div>
        )}

        {docs === null && loadError && (
          <div role="alert" className="border-l-4 border-vermilion-500 bg-[#F8E9E3] px-5 py-5">
            <p className="font-display text-2xl text-carbon-950">Documents could not be loaded</p>
            <p className="mt-1 text-sm text-carbon-500">{loadError}</p>
            <button type="button" onClick={() => loadDocuments({ reportError: true })} className="mt-4 min-h-10 bg-vermilion-500 px-4 text-xs font-semibold text-white hover:bg-vermilion-600 focus-visible:outline-none">Retry loading documents</button>
          </div>
        )}

        {docs?.length === 0 && !loadError && (
          <EmptyState icon={FileText} title="The archive is empty" description="Upload HR, IT, Finance, or operations documents to give the assistant an evidence base." action={<button type="button" onClick={() => setShowUpload(true)} className="mt-5 min-h-10 bg-vermilion-500 px-4 text-sm font-semibold text-white hover:bg-vermilion-600 focus-visible:outline-none">Upload your first document</button>} />
        )}

        {docs?.length > 0 && filteredDocs.length === 0 && !loadError && (
          <EmptyState icon={Search} title="No matching records" description="Try a different file name, category, or status." action={<button type="button" onClick={() => { setQuery(""); setCategory("all"); setStatus("all"); }} className="mt-5 min-h-10 border border-carbon-950 px-4 text-sm font-semibold text-carbon-950 hover:bg-carbon-950 hover:text-canvas-50 focus-visible:outline-none">Clear filters</button>} />
        )}

        {filteredDocs.length > 0 && (
          <section aria-label="Document index" className="border-t border-carbon-950">
            <div className="hidden grid-cols-[3rem_minmax(0,1fr)_8rem_9rem_8rem_3rem] border-b border-carbon-950 px-2 py-2 font-mono text-[8px] uppercase tracking-[0.16em] text-carbon-500 md:grid">
              <span>No.</span><span>Document</span><span>Category</span><span>Indexed</span><span>Status</span><span />
            </div>
            {filteredDocs.map((doc, index) => {
              const meta = STATUS_META[doc.status] || STATUS_META.processing;
              const StatusIcon = meta.icon;
              const isOpen = expanded === doc.id;
              const isPendingDelete = pendingDelete?.id === doc.id;
              return (
                <article key={doc.id} className="border-b border-canvas-300 bg-canvas-50/55 transition-colors hover:bg-canvas-50">
                  <div className="flex items-stretch">
                    <button type="button" aria-expanded={isOpen} aria-controls={`chunks-${doc.id}`} aria-label={`${isOpen ? "Hide" : "Show"} chunks for ${doc.filename}`} onClick={() => toggleExpand(doc)} className="grid min-h-20 min-w-0 flex-1 grid-cols-[2.25rem_minmax(0,1fr)_auto] items-center gap-2 px-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-vermilion-500 md:grid-cols-[3rem_minmax(0,1fr)_8rem_9rem_8rem]">
                      <span className="font-display text-xl italic text-vermilion-500">{String(index + 1).padStart(2, "0")}</span>
                      <span className="min-w-0 pr-2">
                        <span className="block truncate font-display text-xl leading-tight text-carbon-950">{doc.filename}</span>
                        <span className="mt-1 block truncate font-mono text-[9px] uppercase tracking-[0.1em] text-carbon-500">{doc.chunk_count ?? 0} chunks · {Number(doc.char_count || 0).toLocaleString()} characters</span>
                      </span>
                      <span className="hidden font-mono text-[9px] uppercase tracking-[0.1em] text-carbon-500 md:block">{doc.category || "General"}</span>
                      <span className="hidden text-xs text-carbon-500 md:block">{formatDate(doc.updated_at || doc.created_at)}</span>
                      <span className="flex items-center justify-end gap-2 md:justify-start">
                        <Badge tone={meta.tone}><StatusIcon size={10} className={doc.status === "processing" ? "animate-spin" : ""} aria-hidden="true" /> {meta.label}</Badge>
                        <ChevronRight size={15} className={`text-carbon-500 transition-transform md:hidden ${isOpen ? "rotate-90" : ""}`} aria-hidden="true" />
                      </span>
                    </button>
                    <button type="button" aria-label={`Delete ${doc.filename}`} onClick={() => setPendingDelete(doc)} className="flex w-12 shrink-0 items-center justify-center border-l border-canvas-300 text-carbon-500 transition-colors hover:bg-[#F8E9E3] hover:text-vermilion-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-vermilion-500">
                      <Trash2 size={15} aria-hidden="true" />
                    </button>
                  </div>

                  {isPendingDelete && (
                    <div role="alert" className="flex flex-col gap-3 border-t border-vermilion-400 bg-[#F8E9E3] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                      <p className="text-sm text-carbon-900">Delete <span className="font-semibold">{doc.filename}</span>? This removes its evidence from the archive.</p>
                      <div className="flex shrink-0 gap-2">
                        <button type="button" onClick={() => setPendingDelete(null)} className="min-h-9 border border-carbon-950 px-3 text-xs text-carbon-950 hover:bg-canvas-50 focus-visible:outline-none">Cancel</button>
                        <button type="button" onClick={() => confirmDelete(doc)} className="min-h-9 bg-vermilion-500 px-3 text-xs font-semibold text-white hover:bg-vermilion-600 focus-visible:outline-none">Delete document</button>
                      </div>
                    </div>
                  )}

                  {isOpen && (
                    <div id={`chunks-${doc.id}`} className="animate-rise-in border-t border-canvas-300 bg-canvas-200/50 px-4 py-5 sm:px-8">
                      <div className="mb-3 flex items-center gap-3"><p className="font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Chunk register</p><span className="h-px flex-1 bg-canvas-300" /></div>
                      {doc.error_message && <p className="mb-2 text-xs text-vermilion-600">{doc.error_message}</p>}
                      {chunkErrors[doc.id] && <p role="alert" className="mb-2 text-xs text-vermilion-600">{chunkErrors[doc.id]}</p>}
                      {!chunks[doc.id] && !chunkErrors[doc.id] && <Skeleton className="h-20 w-full rounded-none bg-canvas-300" />}
                      <div className="grid max-h-80 gap-px overflow-y-auto bg-canvas-300 lg:grid-cols-2">
                        {chunks[doc.id]?.map((chunk) => (
                          <div key={chunk.id} className="bg-canvas-50 px-4 py-3">
                            <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.12em] text-vermilion-600">Chunk {chunk.chunk_index}{chunk.section ? ` / ${chunk.section}` : ""}</p>
                            <p className="line-clamp-4 break-words text-xs leading-6 text-carbon-500">{chunk.content}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
          </section>
        )}
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} onUpload={handleUpload} />}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="border-r border-carbon-950 px-3 py-4 last:border-r-0">
      <p className="font-display text-3xl italic leading-none text-carbon-950">{Number(value).toLocaleString()}</p>
      <p className="mt-2 font-mono text-[8px] uppercase tracking-[0.15em] text-carbon-500">{label}</p>
    </div>
  );
}

function FilterSelect({ label, value, onChange, options }) {
  const id = `document-filter-${label.toLowerCase()}`;
  const allLabel = label === "Status" ? "All statuses" : "All categories";
  return (
    <div>
      <label htmlFor={id} className="mb-2 block font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">{label}</label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)} className="min-h-11 w-full border border-carbon-950 bg-canvas-50 px-3 text-xs text-carbon-950 focus:outline-none focus:ring-2 focus:ring-vermilion-500">
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
