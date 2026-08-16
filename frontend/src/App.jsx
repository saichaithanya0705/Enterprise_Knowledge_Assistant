import { useCallback, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { Menu } from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { ChatPage } from "./pages/ChatPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { ToastProvider } from "./context/ToastContext";
import { useToast } from "./context/useToast";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./context/useAuth";
import { PublicOnly, RequireAdmin, RequireAuth } from "./components/RouteGuards";
import { LoginPage } from "./pages/auth/LoginPage";
import { RegisterPage } from "./pages/auth/RegisterPage";
import { DeletedChatsPage } from "./pages/user/DeletedChatsPage";
import { ProfilePage } from "./pages/user/ProfilePage";
import { SettingsPage } from "./pages/user/SettingsPage";
import { AdminLayout } from "./layouts/AdminLayout";
import { AdminOverviewPage } from "./pages/admin/AdminOverviewPage";
import { AdminUsersPage } from "./pages/admin/AdminUsersPage";
import { AdminConversationsPage } from "./pages/admin/AdminConversationsPage";
import { AdminRestoreRequestsPage } from "./pages/admin/AdminRestoreRequestsPage";
import { AdminAuditLogPage } from "./pages/admin/AdminAuditLogPage";
import { chatService } from "./services/chatService";
import { systemService } from "./services/systemService";

const INDEX_STATUS_KEYS = [
  "status", "index_status", "reingest_required", "legacy_collections_present",
  "historical_generations_present", "pending_cleanup", "pending_cleanup_count",
  "cleanup_action", "cleanup_metadata_status", "pending_action", "action_required",
];

function normalizeIndexStatus(status) {
  const nested = status?.index && typeof status.index === "object" ? status.index : {};
  const topLevel = Object.fromEntries(
    INDEX_STATUS_KEYS.filter((key) => status?.[key] !== undefined).map((key) => [key, status[key]]),
  );
  return { ...nested, ...topLevel };
}

function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAdmin, signOut } = useAuth();
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(() => (
    typeof window === "undefined" || typeof window.matchMedia !== "function"
      ? true
      : window.matchMedia("(min-width: 1024px)").matches
  ));
  const [conversations, setConversations] = useState([]);
  const [providerStatus, setProviderStatus] = useState({
    chat_backend: "local_fallback",
    embedding_backend: "local_fallback",
    rerank_backend: "local_fallback",
    indexStatus: {},
  });
  const [systemStatus, setSystemStatus] = useState("checking");
  const toast = useToast();

  const conversationMatch = location.pathname.match(/^\/app\/chats\/([^/]+)$/);
  const activeConversationId = conversationMatch && conversationMatch[1] !== "new"
    ? decodeURIComponent(conversationMatch[1])
    : null;
  const page = location.pathname.startsWith("/app/deleted")
    ? "deleted"
    : location.pathname.startsWith("/app/profile")
      ? "profile"
      : location.pathname.startsWith("/app/settings")
        ? "settings"
        : "chat";

  const loadConversations = useCallback(async () => {
    try {
      setConversations(await chatService.listConversations());
    } catch {
      // Conversation history is best-effort; the main view still renders its error state.
    }
  }, []);

  useEffect(() => {
    loadConversations();
    systemService.status().then((status) => {
      setProviderStatus({
        chat_backend: status.chat_backend || (status.key_gateway_configured ? "configured_unverified" : "local_fallback"),
        embedding_backend: status.embedding_backend || (status.nvidia_configured ? "configured_unverified" : "local_fallback"),
        rerank_backend: status.rerank_backend || (status.nvidia_configured ? "configured_unverified" : "local_fallback"),
        indexStatus: normalizeIndexStatus(status),
      });
      setSystemStatus("ready");
    }).catch(() => setSystemStatus("unavailable"));
  }, [loadConversations]);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return undefined;
    const mediaQuery = window.matchMedia("(min-width: 1024px)");
    const updateViewport = () => setIsDesktop(mediaQuery.matches);
    updateViewport();
    mediaQuery.addEventListener?.("change", updateViewport);
    return () => mediaQuery.removeEventListener?.("change", updateViewport);
  }, []);

  const go = (path) => {
    navigate(path);
    setNavigationOpen(false);
  };
  const handleNavigate = (nextPage) => {
    const paths = {
      chat: "/app/chats/new",
      documents: "/admin/documents",
      deleted: "/app/deleted",
      profile: "/app/profile",
      settings: "/app/settings",
      admin: "/admin",
    };
    go(paths[nextPage] || "/app");
  };
  const handleDeleteConversation = async (id) => {
    try {
      await chatService.deleteConversation(id);
      if (activeConversationId === id) go("/app/chats/new");
      await loadConversations();
      toast.push("Conversation moved to the recovery shelf");
    } catch (error) {
      toast.push(error.message, "error");
    }
  };
  const handleLogout = async () => {
    await signOut();
    navigate("/login", { replace: true });
  };

  const content = page === "deleted"
    ? <DeletedChatsPage />
    : page === "profile"
      ? <ProfilePage />
      : page === "settings"
        ? <SettingsPage />
        : <ChatPage conversationId={activeConversationId} onConversationCreated={(id) => { loadConversations(); go(`/app/chats/${id}`); }} />;
  const pageTitle = page === "deleted" ? "Recovery shelf" : page === "profile" ? "Your profile" : page === "settings" ? "Settings" : "Knowledge desk";

  return (
    <div className="h-[100dvh] w-full overflow-hidden bg-canvas-100 lg:grid lg:grid-cols-[15.5rem_minmax(0,1fr)]">
      <a href="#main-content" className="fixed left-4 top-3 z-[60] -translate-y-20 bg-carbon-950 px-4 py-2 text-sm font-semibold text-canvas-50 transition-transform focus:translate-y-0">Skip to workspace</a>
      <Sidebar
        page={page}
        onNavigate={handleNavigate}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={(id) => go(`/app/chats/${id}`)}
        onNewChat={() => go("/app/chats/new")}
        onDeleteConversation={handleDeleteConversation}
        isOpen={navigationOpen || isDesktop}
        onClose={() => setNavigationOpen(false)}
        systemStatus={systemStatus}
        user={user}
        isAdmin={isAdmin}
        onLogout={handleLogout}
        {...providerStatus}
      />
      <div className="flex h-[100dvh] min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center gap-3 border-b border-canvas-300 bg-canvas-50/95 px-4 backdrop-blur lg:hidden">
          <button type="button" aria-label="Open navigation" onClick={() => setNavigationOpen(true)} className="flex h-10 w-10 items-center justify-center border border-carbon-950 bg-carbon-950 text-canvas-50 transition-all hover:-translate-y-0.5 hover:bg-vermilion-500 focus-visible:outline-none"><Menu size={19} aria-hidden="true" /></button>
          <div className="min-w-0"><p className="truncate font-display text-lg leading-none text-carbon-950">{pageTitle}</p><p className="mt-1 font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Private workspace</p></div>
        </header>
        <main id="main-content" className="min-h-0 flex-1 overflow-hidden">{content}</main>
      </div>
    </div>
  );
}

function RootRedirect() {
  const { loading, isAuthenticated, isAdmin } = useAuth();
  if (loading) return null;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Navigate to={isAdmin ? "/admin" : "/app"} replace />;
}

function ApplicationRoutes() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route element={<PublicOnly />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route path="/app/*" element={<AppShell />} />
      </Route>
      <Route element={<RequireAdmin />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminOverviewPage />} />
          <Route path="users" element={<AdminUsersPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="conversations" element={<AdminConversationsPage />} />
          <Route path="restore-requests" element={<AdminRestoreRequestsPage />} />
          <Route path="audit-log" element={<AdminAuditLogPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <BrowserRouter><ApplicationRoutes /></BrowserRouter>
      </AuthProvider>
    </ToastProvider>
  );
}
