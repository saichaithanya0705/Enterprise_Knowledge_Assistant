import { useEffect, useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import { chatService } from "../services/chatService";
import { MessageBubble, TypingIndicator } from "../components/MessageBubble";
import { ChatInput } from "../components/ChatInput";
import { DebugPanel } from "../components/DebugPanel";
import { EmptyState } from "../components/EmptyState";
import { useToast } from "../context/useToast";

export function ChatPage({ conversationId, onConversationCreated }) {
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [debug, setDebug] = useState(null);
  const bottomRef = useRef(null);
  const activeConversationRef = useRef(conversationId);
  const historyRequestRef = useRef(0);
  const sendingRef = useRef(false);
  const activeSendTokenRef = useRef(null);
  const { push: pushToast } = useToast();

  activeConversationRef.current = conversationId;

  useEffect(() => {
    const requestId = ++historyRequestRef.current;
    let cancelled = false;
    setDebug(null);
    setSending(false);
    sendingRef.current = false;
    activeSendTokenRef.current = null;
    if (!conversationId) {
      setMessages([]);
      return () => { cancelled = true; };
    }
    setMessages([]);
    chatService.getMessages(conversationId).then((msgs) => {
      if (!cancelled && requestId === historyRequestRef.current && activeConversationRef.current === conversationId) {
        setMessages(msgs.map((m) => ({
          ...m,
          sources: m.sources || [],
          debug: m.debug || m.debug_trace || null,
        })));
      }
    }).catch((e) => {
      if (!cancelled && requestId === historyRequestRef.current && activeConversationRef.current === conversationId) {
        pushToast(e.message, "error");
      }
    });
    return () => { cancelled = true; };
  }, [conversationId, pushToast]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, sending]);

  const send = async (text, { retryMessageId = null } = {}) => {
    if (sendingRef.current) return;
    const requestConversationId = conversationId;
    const requestViewId = historyRequestRef.current;
    const sendToken = Symbol("chat-send");
    sendingRef.current = true;
    activeSendTokenRef.current = sendToken;
    setMessages((current) => [
      ...(retryMessageId ? current.filter((message) => message.id !== retryMessageId) : current),
      ...(retryMessageId ? [] : [{ id: `tmp-${Date.now()}`, role: "user", content: text }]),
    ]);
    setSending(true);
    try {
      const res = await chatService.send(text, requestConversationId);
      if (
        activeConversationRef.current !== requestConversationId
        || historyRequestRef.current !== requestViewId
      ) return;
      if (!requestConversationId) onConversationCreated(res.conversation_id);
      setMessages((current) => [
        ...current,
        { id: res.message_id, role: "assistant", content: res.answer, sources: res.sources, debug: res.debug },
      ]);
    } catch (e) {
      if (
        activeConversationRef.current === requestConversationId
        && historyRequestRef.current === requestViewId
      ) {
        setMessages((current) => [
          ...current,
          {
            id: `error-${Date.now()}`,
            role: "error",
            content: e.message || "The assistant could not complete that request.",
            retryText: text,
          },
        ]);
      }
    } finally {
      if (activeSendTokenRef.current === sendToken) {
        sendingRef.current = false;
        if (
          activeConversationRef.current === requestConversationId
          && historyRequestRef.current === requestViewId
        ) setSending(false);
      }
    }
  };

  const handleFeedback = async (messageId, rating) => {
    try {
      await chatService.sendFeedback(messageId, rating);
      pushToast(rating > 0 ? "Thanks for the feedback" : "Feedback recorded. We will improve this.");
    } catch (e) {
      pushToast(e.message, "error");
    }
  };

  const handleRegenerate = (index) => {
    if (sendingRef.current) return;
    const lastUser = [...messages.slice(0, index)].reverse().find((m) => m.role === "user");
    if (lastUser) send(lastUser.content);
  };

  return (
    <div className="flex h-full min-h-0 flex-col lg:flex-row">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          {messages.length === 0 && (
            <div className="flex min-h-full items-center justify-center">
              <EmptyState
                icon={Sparkles}
                heading="h1"
                title="Ask your knowledge base"
                description="Get grounded answers from your indexed HR, IT, and Finance documents, with sources you can inspect."
              />
            </div>
          )}
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {messages.map((m, i) => (
              <MessageBubble
                key={m.id}
                message={m}
                onFeedback={handleFeedback}
                onShowDebug={setDebug}
                onRegenerate={m.role === "assistant" ? () => handleRegenerate(i) : null}
                onRetry={m.role === "error" ? () => send(m.retryText, { retryMessageId: m.id }) : null}
                regenerateDisabled={sending}
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
        <div className="fixed inset-0 z-30 bg-black/60 md:static md:h-full md:w-[28rem] md:shrink-0 md:bg-transparent">
          <button
            type="button"
            aria-label="Close RAG trace"
            onClick={() => setDebug(null)}
            className="absolute inset-0 md:hidden"
          />
          <div className="relative z-10 ml-auto h-full w-[min(100%,30rem)] md:ml-0 md:w-full">
            <DebugPanel debug={debug} onClose={() => setDebug(null)} />
          </div>
        </div>
      )}
    </div>
  );
}
