import { useEffect, useMemo, useRef, useState } from "react";
import { BookMarked, FileCheck2, Quote, ShieldCheck, Terminal } from "lucide-react";
import { chatService } from "../services/chatService";
import { MessageBubble, TypingIndicator } from "../components/MessageBubble";
import { ChatInput } from "../components/ChatInput";
import { DebugPanel } from "../components/DebugPanel";
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
      return () => {
        cancelled = true;
      };
    }
    setMessages([]);
    chatService
      .getMessages(conversationId)
      .then((storedMessages) => {
        if (
          !cancelled &&
          requestId === historyRequestRef.current &&
          activeConversationRef.current === conversationId
        ) {
          setMessages(
            storedMessages.map((message) => {
              const sources = message.sources || [];
              return {
                ...message,
                sources,
                grounded:
                  typeof message.grounded === "boolean"
                    ? message.grounded
                    : message.role === "assistant"
                      ? sources.length > 0
                      : undefined,
                debug: message.debug || message.debug_trace || null,
              };
            }),
          );
        }
      })
      .catch((error) => {
        if (
          !cancelled &&
          requestId === historyRequestRef.current &&
          activeConversationRef.current === conversationId
        ) {
          pushToast(error.message, "error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId, pushToast]);

  useEffect(() => {
    if (messages.length > 0 || sending) {
      bottomRef.current?.scrollIntoView?.({ behavior: "smooth" });
    }
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
      const response = await chatService.send(text, requestConversationId);
      if (
        activeConversationRef.current !== requestConversationId ||
        historyRequestRef.current !== requestViewId
      ) {
        return;
      }
      if (!requestConversationId) {
        onConversationCreated(response.conversation_id);
      }
      setMessages((current) => [
        ...current,
        {
          id: response.message_id,
          role: "assistant",
          content: response.answer,
          sources: response.sources || [],
          grounded:
            typeof response.grounded === "boolean"
              ? response.grounded
              : Boolean(response.sources?.length),
          debug: response.debug,
        },
      ]);
    } catch (error) {
      if (
        activeConversationRef.current === requestConversationId &&
        historyRequestRef.current === requestViewId
      ) {
        setMessages((current) => [
          ...current,
          {
            id: `error-${Date.now()}`,
            role: "error",
            content: error.message || "The assistant could not complete that request.",
            retryText: text,
          },
        ]);
      }
    } finally {
      if (activeSendTokenRef.current === sendToken) {
        sendingRef.current = false;
        if (
          activeConversationRef.current === requestConversationId &&
          historyRequestRef.current === requestViewId
        ) {
          setSending(false);
        }
      }
    }
  };

  const handleFeedback = async (messageId, rating) => {
    try {
      await chatService.sendFeedback(messageId, rating);
      pushToast(
        rating > 0 ? "Thanks for the feedback" : "Feedback recorded. We will improve this.",
      );
    } catch (error) {
      pushToast(error.message, "error");
    }
  };

  const handleRegenerate = (index) => {
    if (sendingRef.current) return;
    const lastUser = [...messages.slice(0, index)]
      .reverse()
      .find((message) => message.role === "user");
    if (lastUser) {
      send(lastUser.content);
    }
  };

  const latestAnswer = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant") || null,
    [messages],
  );

  return (
    <div className="grid h-full min-h-0 bg-canvas-100 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="flex min-h-0 min-w-0 flex-col">
        <header className="hidden h-16 shrink-0 items-center justify-between border-b border-canvas-300 bg-canvas-50/75 px-7 sm:flex">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-vermilion-600">
              Desk / Inquiry
            </span>
            <span className="h-px w-10 bg-canvas-300" />
            <span className="text-xs text-carbon-500">
              Answers checked against your private archive
            </span>
          </div>
          <div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.14em] text-carbon-500">
            <span className="h-2 w-2 bg-moss-500" /> Evidence mode
          </div>
        </header>

        <div className="editorial-grid min-h-0 flex-1 overflow-y-auto px-4 py-7 sm:px-7 sm:py-10">
          {messages.length === 0 && <ConversationIntro />}
          <div className="mx-auto flex max-w-4xl flex-col gap-8">
            {messages.map((message, index) => (
              <MessageBubble
                key={message.id}
                message={message}
                onFeedback={handleFeedback}
                onShowDebug={setDebug}
                onRegenerate={
                  message.role === "assistant" ? () => handleRegenerate(index) : null
                }
                onRetry={
                  message.role === "error"
                    ? () => send(message.retryText, { retryMessageId: message.id })
                    : null
                }
                regenerateDisabled={sending}
              />
            ))}
            {sending && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        </div>
        <ChatInput onSend={send} disabled={sending} showSuggestions={messages.length === 0} />
      </div>

      <EvidenceRail answer={latestAnswer} onShowDebug={setDebug} />

      {debug && (
        <div className="fixed inset-0 z-50 bg-carbon-950/55 backdrop-blur-[2px]">
          <button
            type="button"
            aria-label="Close RAG trace"
            onClick={() => setDebug(null)}
            className="absolute inset-0"
          />
          <div className="relative z-10 ml-auto h-full w-[min(100%,32rem)] shadow-lift">
            <DebugPanel debug={debug} onClose={() => setDebug(null)} />
          </div>
        </div>
      )}
    </div>
  );
}

function ConversationIntro() {
  return (
    <section
      className="mx-auto mb-12 max-w-4xl animate-rise-in"
      aria-labelledby="knowledge-desk-title"
    >
      <div className="grid gap-8 border-b border-carbon-950 pb-9 md:grid-cols-[minmax(0,1.5fr)_minmax(15rem,.65fr)] md:gap-12">
        <div>
          <div className="mb-5 flex items-center gap-3">
            <span className="font-mono text-[9px] uppercase tracking-[0.24em] text-vermilion-600">
              Private research desk
            </span>
            <span className="h-px w-16 bg-vermilion-500" />
          </div>
          <h1
            id="knowledge-desk-title"
            className="max-w-3xl text-balance font-display text-[clamp(3.4rem,7vw,6.8rem)] leading-[0.82] tracking-[-0.055em] text-carbon-950"
          >
            Answers,
            <br />
            <span className="italic text-vermilion-500">with receipts.</span>
          </h1>
          <p className="mt-7 max-w-xl text-pretty text-base leading-7 text-carbon-500">
            Ask a policy question in plain language. The desk searches your indexed HR, IT,
            Finance, and operations documents, then shows cited evidence when it is
            available.
          </p>
        </div>

        <div className="flex flex-col justify-end border-l border-canvas-300 pl-5">
          <Quote
            size={24}
            strokeWidth={1.3}
            className="mb-6 text-vermilion-500"
            aria-hidden="true"
          />
          <p className="font-display text-xl italic leading-snug text-carbon-900">
            “The answer is only as useful as the source you can verify.”
          </p>
          <div className="mt-7 space-y-3 border-t border-canvas-300 pt-4">
            <IntroFact icon={ShieldCheck} label="Private by design" />
            <IntroFact icon={FileCheck2} label="Source-linked responses" />
            <IntroFact icon={BookMarked} label="Inspectable retrieval trace" />
          </div>
        </div>
      </div>
    </section>
  );
}

function IntroFact({ icon: Icon, label }) {
  return (
    <div className="flex items-center gap-2.5 text-xs text-carbon-500">
      <Icon size={14} className="text-moss-500" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

function EvidenceRail({ answer, onShowDebug }) {
  const sources = answer?.sources || [];

  return (
    <aside
      aria-label="Evidence workspace"
      className="hidden min-h-0 flex-col border-l border-canvas-300 bg-canvas-50 xl:flex"
    >
      <div className="border-b border-canvas-300 px-5 py-5">
        <p className="font-mono text-[9px] uppercase tracking-[0.22em] text-vermilion-600">
          Evidence ledger
        </p>
        <h2 className="mt-1 font-display text-2xl text-carbon-950">Sources in view</h2>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        {sources.length === 0 ? (
          <div className="border-l-2 border-canvas-300 pl-4">
            <p className="font-display text-lg italic text-carbon-900">No evidence selected</p>
            <p className="mt-2 text-xs leading-6 text-carbon-500">
              Ask a question and the cited passages will collect here for quick review.
            </p>
          </div>
        ) : (
          <ol className="space-y-5">
            {sources.map((source, index) => (
              <li
                key={source.chunk_id || `${source.filename}-${index}`}
                className="border-t border-carbon-950 pt-3"
              >
                <div className="flex items-start gap-3">
                  <span className="font-display text-2xl italic leading-none text-vermilion-500">
                    {index + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="break-words text-sm font-semibold text-carbon-950">
                      {source.filename}
                    </p>
                    <p className="mt-1 font-mono text-[9px] uppercase tracking-[0.12em] text-carbon-500">
                      {source.section || "Document excerpt"}
                    </p>
                  </div>
                </div>
                {source.excerpt && (
                  <p className="mt-3 line-clamp-4 text-xs leading-5 text-carbon-500">
                    {source.excerpt}
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>
      <div className="border-t border-canvas-300 p-5">
        <div className="mb-3 flex items-center justify-between font-mono text-[9px] uppercase tracking-[0.14em] text-carbon-500">
          <span>Citations</span>
          <span>{String(sources.length).padStart(2, "0")}</span>
        </div>
        <button
          type="button"
          onClick={() => answer?.debug && onShowDebug(answer.debug)}
          disabled={!answer?.debug}
          className="flex min-h-10 w-full items-center justify-between border border-carbon-950 px-3 text-xs font-semibold text-carbon-950 transition-all hover:bg-carbon-950 hover:text-canvas-50 disabled:cursor-not-allowed disabled:border-canvas-300 disabled:text-carbon-500"
        >
          Inspect retrieval <Terminal size={14} aria-hidden="true" />
        </button>
      </div>
    </aside>
  );
}
