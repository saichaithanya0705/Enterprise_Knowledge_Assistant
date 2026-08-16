import { MessageSquarePlus, Library, MessagesSquare, Trash2, BookOpenText, X } from "lucide-react";
import { Badge } from "./Badge";

const STATUS_LABELS = {
  configured_unverified: "configured (unverified)",
  local_fallback: "local fallback",
  key_gateway: "configured (unverified)",
  nvidia: "configured (unverified)",
};

function displayStatus(status, configured) {
  return STATUS_LABELS[status] || STATUS_LABELS[configured ? "configured_unverified" : "local_fallback"];
}

export function Sidebar({
  page,
  onNavigate,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  chat_backend,
  embedding_backend,
  rerank_backend,
  chatBackend,
  embeddingBackend,
  rerankBackend,
  gatewayConfigured,
  nvidiaConfigured,
  indexStatus,
  systemStatus = "ready",
  isOpen = true,
  onClose = () => {},
}) {
  const chatStatus = displayStatus(chatBackend ?? chat_backend, gatewayConfigured);
  const embeddingStatus = displayStatus(embeddingBackend ?? embedding_backend, nvidiaConfigured);
  const rerankStatus = displayStatus(rerankBackend ?? rerank_backend, nvidiaConfigured);
  const lifecycle = indexStatus || {};
  const indexState = lifecycle.index_status
    || (lifecycle.status === "degraded" ? "degraded" : "unknown");
  const pendingCleanup = lifecycle.pending_cleanup_count ?? lifecycle.pending_cleanup;
  const pendingCleanupExists = Array.isArray(pendingCleanup)
    ? pendingCleanup.length > 0
    : Number.isFinite(Number(pendingCleanup))
      ? Number(pendingCleanup) > 0
      : Boolean(pendingCleanup);
  const indexNeedsAttention = Boolean(
    lifecycle.reingest_required
      || lifecycle.legacy_collections_present
      || lifecycle.historical_generations_present
      || pendingCleanupExists
      || lifecycle.cleanup_action
      || lifecycle.pending_action
      || lifecycle.action_required
      || lifecycle.cleanup_metadata_status === "unavailable"
      || lifecycle.status === "degraded"
      || ["empty", "degraded", "incomplete", "reingest_required", "unavailable", "error", "failed"].includes(indexState),
  );
  const indexMessage = lifecycle.cleanup_metadata_status === "unavailable"
    ? "Index cleanup metadata is unavailable; system health is degraded until it can be checked."
    : lifecycle.reingest_required || lifecycle.index_status === "reingest_required"
    ? "Semantic index coverage is incomplete; reingest documents before relying on semantic search."
    : lifecycle.index_status === "unavailable"
      ? "Semantic index status is unavailable; semantic search may be degraded."
      : "Semantic index coverage is degraded; review the available index action before relying on semantic search.";
  const actionDetail = lifecycle.cleanup_action || lifecycle.pending_action || lifecycle.action_required;
  const systemUnavailable = systemStatus === "unavailable";
  const systemChecking = systemStatus === "checking";
  const systemTone = systemUnavailable || indexNeedsAttention ? "amber" : "teal";
  const systemLabel = systemUnavailable ? "Unavailable" : systemChecking ? "Checking" : indexNeedsAttention ? "Needs attention" : "Ready";

  return (
    <>
      {isOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={onClose}
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
        />
      )}
      <aside
        aria-label="Workspace navigation"
        aria-hidden={!isOpen}
        inert={isOpen ? undefined : true}
        className={`fixed inset-y-0 left-0 z-40 flex h-[100dvh] w-[min(18rem,calc(100vw-2rem))] shrink-0 flex-col border-r border-ink-600 bg-ink-950 shadow-card transition-transform duration-200 lg:relative lg:z-auto lg:w-72 lg:translate-x-0 lg:shadow-none ${isOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
      <div className="flex items-start gap-3 px-4 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500">
          <BookOpenText size={16} className="text-ink-950" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className="font-display text-sm leading-tight text-paper-100">Knowledge Assistant</p>
            <button
              type="button"
              aria-label="Close navigation"
              onClick={onClose}
              className="-mr-1 -mt-1 flex h-8 w-8 items-center justify-center rounded-lg text-paper-500 hover:bg-ink-800 hover:text-paper-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 lg:hidden"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
          <p className="mt-1 text-xs text-paper-500">Private knowledge workspace</p>
          <p data-testid="provider-status" className="sr-only">
            chat: {chatStatus} · embeddings: {embeddingStatus} · rerank: {rerankStatus}
          </p>
          <p data-testid="index-status" className="sr-only">index: {indexState}</p>
        </div>
      </div>

      <div className="mx-3 mb-3 rounded-xl border border-ink-600 bg-ink-900/70 px-3 py-2.5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] font-medium text-paper-300">System status</span>
          <Badge tone={systemTone}>{systemLabel}</Badge>
        </div>
        <p className="mt-1 text-[11px] leading-relaxed text-paper-500">
          {systemUnavailable
            ? "The workspace health check could not be completed."
            : systemChecking
              ? "Checking chat and document search availability."
              : indexNeedsAttention
                ? "Index coverage needs review before semantic search."
                : "Chat and document search are ready."}
        </p>
      </div>

      {indexNeedsAttention && (
        <div role="alert" className="mx-3 mb-3 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2.5 text-xs text-amber-200">
          <p>{indexMessage}</p>
          {actionDetail && <p className="mt-1 font-mono text-[10px]">Action: {String(actionDetail)}</p>}
          <button type="button" onClick={() => { onNavigate("documents"); onClose(); }} className="mt-2 rounded-md px-2 py-1 text-[11px] font-medium text-amber-100 ring-1 ring-inset ring-amber-400/40 hover:bg-amber-400/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300">
            Review documents
          </button>
        </div>
      )}

      <nav className="px-3 space-y-1">
        <button
          type="button"
          onClick={() => { onNewChat(); onClose(); }}
          className="flex min-h-10 w-full items-center gap-2 rounded-lg bg-amber-500 px-3 py-2 text-sm font-semibold text-ink-950 transition-colors hover:bg-amber-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-950"
        >
          <MessageSquarePlus size={15} /> New chat
        </button>
        <button
          type="button"
          onClick={() => { onNavigate("documents"); onClose(); }}
          className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
            page === "documents" ? "bg-ink-700 text-paper-100" : "text-paper-300 hover:bg-ink-800"
          }`}
        >
          <Library size={15} /> Documents
        </button>
      </nav>

      <div className="mt-4 flex-1 overflow-y-auto px-3">
        <p className="px-1 pb-2 text-xs font-medium text-paper-500">Conversations</p>
        <div className="space-y-0.5">
          {conversations.length === 0 && (
            <p className="px-1 py-2 text-xs text-paper-500">No conversations yet.</p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`group flex items-center gap-2 rounded-lg px-2 py-2 transition-colors ${
                page === "chat" && activeConversationId === c.id ? "bg-ink-700 text-paper-100" : "text-paper-300 hover:bg-ink-800"
              }`}
            >
              <button
                type="button"
                aria-label={`Open conversation ${c.title}`}
                onClick={() => onSelectConversation(c.id)}
                className="flex min-h-9 min-w-0 flex-1 items-center gap-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-inset"
              >
                <MessagesSquare size={13} className="shrink-0 text-paper-500" />
                <span className="truncate text-xs">{c.title}</span>
              </button>
              <button
                type="button"
                aria-label={`Delete conversation ${c.title}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteConversation(c.id);
                }}
                className="flex h-8 w-8 items-center justify-center text-paper-500 transition-colors hover:text-coral-500 focus-visible:opacity-100 group-focus-within:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral-400 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100 lg:focus-visible:opacity-100"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-ink-600 px-4 py-3">
        <p className="text-[10px] leading-relaxed text-paper-500">
          Answers are grounded in your uploaded HR, IT, and Finance documents.
        </p>
      </div>
      </aside>
    </>
  );
}
