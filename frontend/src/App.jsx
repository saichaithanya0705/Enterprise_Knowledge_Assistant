import { useEffect, useState, useCallback } from "react";
import { Menu } from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { ChatPage } from "./pages/ChatPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { ToastProvider } from "./context/ToastContext";
import { useToast } from "./context/useToast";
import { chatService } from "./services/chatService";
import { systemService } from "./services/systemService";

const INDEX_STATUS_KEYS = [
  "status",
  "index_status",
  "reingest_required",
  "legacy_collections_present",
  "historical_generations_present",
  "pending_cleanup",
  "pending_cleanup_count",
  "cleanup_action",
  "cleanup_metadata_status",
  "pending_action",
  "action_required",
];

function normalizeIndexStatus(status) {
  const nested = status?.index && typeof status.index === "object" ? status.index : {};
  const topLevel = Object.fromEntries(
    INDEX_STATUS_KEYS
      .filter((key) => status?.[key] !== undefined)
      .map((key) => [key, status[key]]),
  );
  return { ...nested, ...topLevel };
}

function AppShell() {
  const [page, setPage] = useState("chat");
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
    return window.matchMedia("(min-width: 1024px)").matches;
  });
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [providerStatus, setProviderStatus] = useState({
    chat_backend: "local_fallback",
    embedding_backend: "local_fallback",
    rerank_backend: "local_fallback",
    indexStatus: {},
  });
  const [systemStatus, setSystemStatus] = useState("checking");
  const toast = useToast();

  const loadConversations = useCallback(async () => {
    try {
      setConversations(await chatService.listConversations());
    } catch {
      // conversation list is best-effort; chat still works without it
    }
  }, []);

  useEffect(() => {
    loadConversations();
    systemService.status().then((s) => {
      setProviderStatus({
        chat_backend: s.chat_backend || (s.key_gateway_configured ? "configured_unverified" : "local_fallback"),
        embedding_backend: s.embedding_backend || (s.nvidia_configured ? "configured_unverified" : "local_fallback"),
        rerank_backend: s.rerank_backend || (s.nvidia_configured ? "configured_unverified" : "local_fallback"),
        indexStatus: normalizeIndexStatus(s),
      });
      setSystemStatus("ready");
    }).catch(() => {
      setSystemStatus("unavailable");
    });
  }, [loadConversations]);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return undefined;
    const mediaQuery = window.matchMedia("(min-width: 1024px)");
    const updateViewport = () => setIsDesktop(mediaQuery.matches);
    updateViewport();
    mediaQuery.addEventListener?.("change", updateViewport);
    return () => mediaQuery.removeEventListener?.("change", updateViewport);
  }, []);

  const handleNewChat = () => {
    setActiveConversationId(null);
    setPage("chat");
    setNavigationOpen(false);
  };

  const handleSelectConversation = (id) => {
    setActiveConversationId(id);
    setPage("chat");
    setNavigationOpen(false);
  };

  const handleConversationCreated = (id) => {
    setActiveConversationId(id);
    loadConversations();
  };

  const handleNavigate = (nextPage) => {
    setPage(nextPage);
    setNavigationOpen(false);
  };

  const handleDeleteConversation = async (id) => {
    try {
      await chatService.deleteConversation(id);
      if (activeConversationId === id) setActiveConversationId(null);
      loadConversations();
      toast.push("Conversation deleted");
    } catch (e) {
      toast.push(e.message, "error");
    }
  };

  return (
    <div className="min-h-[100dvh] w-full overflow-hidden bg-ink-900 lg:flex">
      <Sidebar
        page={page}
        onNavigate={handleNavigate}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        isOpen={navigationOpen || isDesktop}
        onClose={() => setNavigationOpen(false)}
        systemStatus={systemStatus}
        {...providerStatus}
      />
      <div className="flex min-h-[100dvh] min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-ink-600 bg-ink-900/95 px-4 backdrop-blur lg:hidden">
          <button
            type="button"
            aria-label="Open navigation"
            onClick={() => setNavigationOpen(true)}
            className="flex h-10 w-10 items-center justify-center rounded-lg text-paper-300 transition-colors hover:bg-ink-800 hover:text-paper-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
          >
            <Menu size={19} aria-hidden="true" />
          </button>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-paper-100">{page === "chat" ? "Ask the knowledge base" : "Documents"}</p>
            <p className="text-[11px] text-paper-500">Private workspace</p>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-hidden">
          {page === "chat" ? (
            <ChatPage conversationId={activeConversationId} onConversationCreated={handleConversationCreated} />
          ) : (
            <DocumentsPage />
          )}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AppShell />
    </ToastProvider>
  );
}
