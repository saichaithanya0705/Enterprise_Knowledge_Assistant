import { useEffect, useState, useCallback } from "react";
import { Sidebar } from "./components/Sidebar";
import { ChatPage } from "./pages/ChatPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { ToastProvider, useToast } from "./context/ToastContext";
import { chatService } from "./services/chatService";
import { systemService } from "./services/systemService";

function AppShell() {
  const [page, setPage] = useState("chat");
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [gatewayConfigured, setGatewayConfigured] = useState(false);
  const [nvidiaConfigured, setNvidiaConfigured] = useState(false);
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
      setGatewayConfigured(s.key_gateway_configured);
      setNvidiaConfigured(s.nvidia_configured);
    }).catch(() => {});
  }, [loadConversations]);

  const handleNewChat = () => {
    setActiveConversationId(null);
    setPage("chat");
  };

  const handleSelectConversation = (id) => {
    setActiveConversationId(id);
    setPage("chat");
  };

  const handleConversationCreated = (id) => {
    setActiveConversationId(id);
    loadConversations();
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
    <div className="flex h-screen w-screen overflow-hidden">
      <Sidebar
        page={page}
        onNavigate={setPage}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        gatewayConfigured={gatewayConfigured}
        nvidiaConfigured={nvidiaConfigured}
      />
      <main className="flex-1 overflow-hidden">
        {page === "chat" ? (
          <ChatPage conversationId={activeConversationId} onConversationCreated={handleConversationCreated} />
        ) : (
          <DocumentsPage />
        )}
      </main>
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
