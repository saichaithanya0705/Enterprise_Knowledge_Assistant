import { ArchiveRestore, BookOpenText, LibraryBig, LogOut, MessageCircleQuestion, MessagesSquare, Plus, Settings, ShieldCheck, Trash2, UserRound, X } from "lucide-react";
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
  user,
  isAdmin = false,
  onLogout = () => {},
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
  const systemLabel = systemUnavailable ? "Unavailable" : systemChecking ? "Checking" : indexNeedsAttention ? "Review" : "Ready";

  return (
    <>
      {isOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={onClose}
          className="fixed inset-0 z-30 bg-carbon-950/55 backdrop-blur-[2px] lg:hidden"
        />
      )}
      <aside
        aria-label="Workspace navigation"
        aria-hidden={!isOpen}
        inert={isOpen ? undefined : true}
        className={`fixed inset-y-0 left-0 z-40 flex h-[100dvh] w-[min(20rem,calc(100vw-1.25rem))] shrink-0 flex-col overflow-hidden border-r border-white/10 bg-carbon-950 text-canvas-50 shadow-lift transition-transform duration-300 lg:relative lg:z-auto lg:w-[15.5rem] lg:translate-x-0 lg:shadow-none ${isOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="relative border-b border-white/10 px-5 pb-5 pt-6">
          <div className="absolute left-0 top-0 h-full w-1 bg-vermilion-500" />
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center border border-white/20 font-display text-xl italic text-canvas-50">KA</div>
              <div className="min-w-0">
                <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-canvas-500">Folio 01</p>
                <p className="mt-1 font-display text-lg leading-[0.95] text-canvas-50">Knowledge<br />Assistant</p>
              </div>
            </div>
            <button type="button" aria-label="Close navigation" onClick={onClose} className="-mr-2 -mt-2 flex h-9 w-9 items-center justify-center text-canvas-500 transition-colors hover:bg-white/10 hover:text-canvas-50 focus-visible:outline-none lg:hidden">
              <X size={17} aria-hidden="true" />
            </button>
          </div>
          <p data-testid="provider-status" className="sr-only">chat: {chatStatus} · embeddings: {embeddingStatus} · rerank: {rerankStatus}</p>
          <p data-testid="index-status" className="sr-only">index: {indexState}</p>
        </div>

        <nav aria-label="Primary" className="space-y-1 px-3 py-4">
          <button type="button" onClick={() => { onNewChat(); onClose(); }} className="group flex min-h-11 w-full items-center justify-between bg-vermilion-500 px-3.5 text-sm font-semibold text-white transition-all duration-200 hover:-translate-y-0.5 hover:bg-vermilion-400 focus-visible:outline-none">
            <span className="flex items-center gap-2.5"><Plus size={16} aria-hidden="true" /> New inquiry</span>
            <span className="font-mono text-[10px] opacity-65">01</span>
          </button>
          <button type="button" onClick={() => { onNavigate("chat"); onClose(); }} className={`flex min-h-10 w-full items-center gap-2.5 border-l-2 px-3 text-sm transition-all ${page === "chat" ? "border-vermilion-500 bg-white/10 text-white" : "border-transparent text-canvas-300 hover:border-white/25 hover:bg-white/5 hover:text-white"}`}>
            <MessageCircleQuestion size={15} aria-hidden="true" /> Ask the desk
          </button>
          {isAdmin && <button type="button" onClick={() => { onNavigate("documents"); onClose(); }} className="flex min-h-10 w-full items-center gap-2.5 border-l-2 border-transparent px-3 text-sm text-canvas-300 transition-all hover:border-white/25 hover:bg-white/5 hover:text-white"><LibraryBig size={15} aria-hidden="true" /> Document library</button>}
          <button type="button" onClick={() => { onNavigate("deleted"); onClose(); }} className={`flex min-h-10 w-full items-center gap-2.5 border-l-2 px-3 text-sm transition-all ${page === "deleted" ? "border-vermilion-500 bg-white/10 text-white" : "border-transparent text-canvas-300 hover:border-white/25 hover:bg-white/5 hover:text-white"}`}><ArchiveRestore size={15} aria-hidden="true" /> Recovery shelf</button>
          <button type="button" onClick={() => { onNavigate("profile"); onClose(); }} className={`flex min-h-10 w-full items-center gap-2.5 border-l-2 px-3 text-sm transition-all ${page === "profile" ? "border-vermilion-500 bg-white/10 text-white" : "border-transparent text-canvas-300 hover:border-white/25 hover:bg-white/5 hover:text-white"}`}><UserRound size={15} aria-hidden="true" /> Profile</button>
          <button type="button" onClick={() => { onNavigate("settings"); onClose(); }} className={`flex min-h-10 w-full items-center gap-2.5 border-l-2 px-3 text-sm transition-all ${page === "settings" ? "border-vermilion-500 bg-white/10 text-white" : "border-transparent text-canvas-300 hover:border-white/25 hover:bg-white/5 hover:text-white"}`}><Settings size={15} aria-hidden="true" /> Settings</button>
          {isAdmin && <button type="button" onClick={() => { onNavigate("admin"); onClose(); }} className="flex min-h-10 w-full items-center gap-2.5 border-l-2 border-transparent px-3 text-sm text-canvas-300 transition-all hover:border-white/25 hover:bg-white/5 hover:text-white"><ShieldCheck size={15} aria-hidden="true" /> Admin control</button>}
        </nav>

        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
          <div className="mb-2 flex items-center justify-between border-b border-white/10 px-1 pb-2">
            <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-canvas-500">Recent notes</p>
            <span className="font-mono text-[9px] text-canvas-500">{String(conversations.length).padStart(2, "0")}</span>
          </div>
          <div className="space-y-px">
            {conversations.length === 0 && (
              <div className="border-l border-white/10 px-3 py-5">
                <BookOpenText size={15} className="mb-2 text-canvas-500" aria-hidden="true" />
                <p className="text-xs leading-relaxed text-canvas-500">Your inquiry history will be indexed here.</p>
              </div>
            )}
            {conversations.map((conversation, index) => (
              <div key={conversation.id} className={`group flex items-center border-l-2 transition-colors ${page === "chat" && activeConversationId === conversation.id ? "border-vermilion-500 bg-white/10 text-white" : "border-transparent text-canvas-300 hover:border-white/20 hover:bg-white/5"}`}>
                <button type="button" aria-label={`Open conversation ${conversation.title}`} onClick={() => onSelectConversation(conversation.id)} className="flex min-h-11 min-w-0 flex-1 items-center gap-2.5 px-3 text-left focus-visible:outline-none">
                  <span className="w-5 shrink-0 font-mono text-[9px] text-canvas-500">{String(index + 1).padStart(2, "0")}</span>
                  <MessagesSquare size={13} className="shrink-0 text-canvas-500" aria-hidden="true" />
                  <span className="truncate text-xs">{conversation.title}</span>
                </button>
                <button type="button" aria-label={`Delete conversation ${conversation.title}`} onClick={(event) => { event.stopPropagation(); onDeleteConversation(conversation.id); }} className="mr-1 flex h-8 w-8 items-center justify-center text-canvas-500 opacity-100 transition-colors hover:bg-vermilion-500/15 hover:text-vermilion-400 focus-visible:opacity-100 group-focus-within:opacity-100 focus-visible:outline-none lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100 lg:focus-visible:opacity-100">
                  <Trash2 size={12} aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="border-t border-white/10 bg-carbon-900 px-4 py-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 ${systemUnavailable || indexNeedsAttention ? "bg-amber-400" : "bg-moss-400"}`} />
              <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-canvas-300">System</span>
            </div>
            <Badge tone={systemTone}>{systemLabel}</Badge>
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-canvas-500">
            {systemUnavailable ? "Workspace health could not be checked." : systemChecking ? "Checking workspace availability." : indexNeedsAttention ? "The evidence index needs review." : "Grounded search is ready."}
          </p>
          {indexNeedsAttention && (
            <div role="alert" className="mt-3 border-l-2 border-amber-400 bg-amber-500/10 px-3 py-2.5 text-[11px] leading-relaxed text-amber-200">
              <p>{indexMessage}</p>
              {actionDetail && <p className="mt-1 break-words font-mono text-[9px] text-amber-400">Action: {String(actionDetail)}</p>}
              <button type="button" onClick={() => { onNavigate("documents"); onClose(); }} className="mt-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-amber-100 underline decoration-amber-400/60 underline-offset-4 focus-visible:outline-none">Review library</button>
            </div>
          )}
          <div className="mt-4 flex items-center justify-between gap-3 border-t border-white/10 pt-4">
            <div className="min-w-0"><p className="truncate text-xs text-canvas-100">{user?.name || "Workspace member"}</p><p className="truncate font-mono text-[8px] uppercase tracking-[0.12em] text-canvas-500">{user?.role || "USER"}</p></div>
            <button type="button" aria-label="Sign out" onClick={onLogout} className="flex h-9 w-9 shrink-0 items-center justify-center border border-white/15 text-canvas-500 hover:bg-white/10 hover:text-white focus-visible:outline-none"><LogOut size={14} aria-hidden="true" /></button>
          </div>
        </div>
      </aside>
    </>
  );
}
