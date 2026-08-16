import { useEffect, useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import { chatService } from "../services/chatService";
import { MessageBubble, TypingIndicator } from "../components/MessageBubble";
import { ChatInput } from "../components/ChatInput";
import { DebugPanel } from "../components/DebugPanel";
import { EmptyState } from "../components/EmptyState";
import { useToast } from "../context/ToastContext";

export function ChatPage({ conversationId, onConversationCreated }) {
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [debug, setDebug] = useState(null);
  const bottomRef = useRef(null);
  const toast = useToast();

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    chatService.getMessages(conversationId).then((msgs) =>
      setMessages(msgs.map((m) => ({ ...m, sources: m.sources || [] })))
    ).catch((e) => toast.push(e.message, "error"));
  }, [conversationId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const send = async (text) => {
    setMessages((m) => [...m, { id: `tmp-${Date.now()}`, role: "user", content: text }]);
    setSending(true);
    try {
      const res = await chatService.send(text, conversationId);
      if (!conversationId) onConversationCreated(res.conversation_id);
      setMessages((m) => [
        ...m,
        { id: res.message_id, role: "assistant", content: res.answer, sources: res.sources, debug: res.debug },
      ]);
    } catch (e) {
      toast.push(e.message, "error");
      setMessages((m) => m.slice(0, -1));
    } finally {
      setSending(false);
    }
  };

  const handleFeedback = async (messageId, rating) => {
    try {
      await chatService.sendFeedback(messageId, rating);
      toast.push(rating > 0 ? "Thanks for the feedback" : "Feedback recorded — we'll improve this");
    } catch (e) {
      toast.push(e.message, "error");
    }
  };

  const handleRegenerate = (index) => {
    const lastUser = [...messages.slice(0, index)].reverse().find((m) => m.role === "user");
    if (lastUser) send(lastUser.content);
  };

  return (
    <div className="flex h-full">
      <div className="flex h-full flex-1 flex-col">
        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          {messages.length === 0 && (
            <EmptyState
              icon={Sparkles}
              title="Ask the Knowledge Assistant anything"
              description="Answers are grounded in your indexed HR, IT, and Finance documents, with sources cited inline."
            />
          )}
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {messages.map((m, i) => (
              <MessageBubble
                key={m.id}
                message={m}
                onFeedback={handleFeedback}
                onShowDebug={setDebug}
                onRegenerate={m.role === "assistant" ? () => handleRegenerate(i) : null}
              />
            ))}
            {sending && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        </div>
        <div className="mx-auto w-full max-w-3xl">
          <ChatInput onSend={send} disabled={sending} showSuggestions={messages.length === 0} />
        </div>
      </div>

      {debug && (
        <div className="hidden md:block h-full">
          <DebugPanel debug={debug} onClose={() => setDebug(null)} />
        </div>
      )}
    </div>
  );
}
