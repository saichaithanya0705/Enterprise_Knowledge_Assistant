import { useEffect, useState } from "react";
import { Plus, FileText, Trash2, ChevronRight, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { documentService } from "../services/documentService";
import { UploadModal } from "../components/UploadModal";
import { EmptyState } from "../components/EmptyState";
import { Skeleton } from "../components/Skeleton";
import { Badge } from "../components/Badge";
import { useToast } from "../context/ToastContext";

const STATUS_META = {
  ready: { icon: CheckCircle2, tone: "teal", label: "Ready" },
  processing: { icon: Loader2, tone: "amber", label: "Processing" },
  failed: { icon: XCircle, tone: "coral", label: "Failed" },
};

export function DocumentsPage() {
  const [docs, setDocs] = useState(null);
  const [showUpload, setShowUpload] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const [chunks, setChunks] = useState({});
  const toast = useToast();

  const load = async () => {
    try {
      setDocs(await documentService.list());
    } catch (e) {
      toast.push(e.message, "error");
    }
  };

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleUpload = async (file, category) => {
    await documentService.upload(file, category);
    toast.push(`${file.name} ingested successfully`);
    load();
  };

  const handleDelete = async (id, name) => {
    try {
      await documentService.remove(id);
      toast.push(`${name} removed`);
      load();
    } catch (e) {
      toast.push(e.message, "error");
    }
  };

  const toggleExpand = async (doc) => {
    if (expanded === doc.id) {
      setExpanded(null);
      return;
    }
    setExpanded(doc.id);
    if (!chunks[doc.id]) {
      const data = await documentService.getChunks(doc.id);
      setChunks((prev) => ({ ...prev, [doc.id]: data }));
    }
  };

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="flex items-center justify-between border-b border-ink-600 px-6 py-4 sm:px-8">
        <div>
          <h1 className="font-display text-xl text-paper-100">Knowledge base documents</h1>
          <p className="mt-0.5 text-sm text-paper-500">
            Every document is chunked, embedded, and indexed before it's searchable in chat.
          </p>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-3.5 py-2 text-sm font-medium text-ink-950 hover:bg-amber-400 transition-colors"
        >
          <Plus size={15} /> Upload
        </button>
      </div>

      <div className="flex-1 px-6 py-6 sm:px-8">
        {docs === null && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
          </div>
        )}

        {docs?.length === 0 && (
          <EmptyState
            icon={FileText}
            title="No documents yet"
            description="Upload HR, IT, or policy documents to power the assistant's answers."
            action={
              <button onClick={() => setShowUpload(true)} className="mt-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-ink-950">
                Upload your first document
              </button>
            }
          />
        )}

        <div className="space-y-2">
          {docs?.map((doc) => {
            const meta = STATUS_META[doc.status] || STATUS_META.processing;
            const StatusIcon = meta.icon;
            const isOpen = expanded === doc.id;
            return (
              <div key={doc.id} className="rounded-xl border border-ink-600 bg-ink-800/60 overflow-hidden">
                <button onClick={() => toggleExpand(doc)} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-ink-700/40 transition-colors">
                  <FileText size={16} className="shrink-0 text-paper-500" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-paper-100">{doc.filename}</p>
                    <p className="text-xs text-paper-500">
                      {doc.category} · {doc.chunk_count} chunks · {doc.char_count.toLocaleString()} chars
                    </p>
                  </div>
                  <Badge tone={meta.tone}>
                    <StatusIcon size={11} className={doc.status === "processing" ? "animate-spin" : ""} /> {meta.label}
                  </Badge>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(doc.id, doc.filename); }}
                    className="text-paper-500 hover:text-coral-500 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                  <ChevronRight size={14} className={`text-paper-500 transition-transform ${isOpen ? "rotate-90" : ""}`} />
                </button>

                {isOpen && (
                  <div className="animate-rise-in border-t border-ink-600 bg-ink-950/40 px-4 py-3">
                    {doc.error_message && <p className="mb-2 text-xs text-coral-500">{doc.error_message}</p>}
                    {!chunks[doc.id] && <Skeleton className="h-20 w-full" />}
                    <div className="space-y-2 max-h-72 overflow-y-auto">
                      {chunks[doc.id]?.map((c) => (
                        <div key={c.id} className="rounded-lg border border-ink-600 bg-ink-800 px-3 py-2">
                          <p className="mb-1 font-mono text-[10px] text-paper-500">
                            chunk {c.chunk_index} {c.section ? `· ${c.section}` : ""}
                          </p>
                          <p className="text-xs text-paper-300 line-clamp-3">{c.content}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} onUpload={handleUpload} />}
    </div>
  );
}
