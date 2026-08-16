import { MessageSquarePlus, Library, MessagesSquare, Trash2, BookOpenText } from "lucide-react";

export function Sidebar({ page, onNavigate, conversations, activeConversationId, onSelectConversation, onNewChat, onDeleteConversation, gatewayConfigured, nvidiaConfigured }) {
  const statusLabel = gatewayConfigured && nvidiaConfigured
    ? "chat + nvidia live"
    : gatewayConfigured || nvidiaConfigured
    ? "partially live"
    : "local demo mode";

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-ink-600 bg-ink-950">
      <div className="flex items-center gap-2 px-4 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500">
          <BookOpenText size={16} className="text-ink-950" />
        </div>
        <div className="min-w-0">
          <p className="font-display text-sm leading-tight text-paper-100">Knowledge Assistant</p>
          <p className="text-[10px] font-mono text-paper-500">{statusLabel}</p>
        </div>
      </div>

      <nav className="px-3 space-y-1">
        <button
          onClick={onNewChat}
          className="flex w-full items-center gap-2 rounded-lg bg-amber-500 px-3 py-2 text-sm font-medium text-ink-950 hover:bg-amber-400 transition-colors"
        >
          <MessageSquarePlus size={15} /> New chat
        </button>
        <button
          onClick={() => onNavigate("documents")}
          className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
            page === "documents" ? "bg-ink-700 text-paper-100" : "text-paper-300 hover:bg-ink-800"
          }`}
        >
          <Library size={15} /> Documents
        </button>
      </nav>

      <div className="mt-4 flex-1 overflow-y-auto px-3">
        <p className="px-1 pb-2 text-[11px] uppercase tracking-wide text-paper-500">Conversations</p>
        <div className="space-y-0.5">
          {conversations.length === 0 && (
            <p className="px-1 py-2 text-xs text-paper-500">No conversations yet.</p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`group flex items-center gap-2 rounded-lg px-2 py-2 cursor-pointer transition-colors ${
                page === "chat" && activeConversationId === c.id ? "bg-ink-700 text-paper-100" : "text-paper-300 hover:bg-ink-800"
              }`}
              onClick={() => onSelectConversation(c.id)}
            >
              <MessagesSquare size={13} className="shrink-0 text-paper-500" />
              <span className="truncate text-xs flex-1">{c.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteConversation(c.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-paper-500 hover:text-coral-500 transition-opacity"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-ink-600 px-4 py-3">
        <p className="text-[10px] text-paper-500 leading-relaxed">
          RAG portfolio project — internal HR/IT knowledge base.
        </p>
      </div>
    </aside>
  );
}
