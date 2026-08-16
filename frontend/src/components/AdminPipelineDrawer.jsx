import { useEffect, useMemo, useState } from "react";
import { X, Activity, MessageSquare } from "lucide-react";
import { DebugPanel } from "./DebugPanel";

const textOf = (value, fallback = "Not available") => typeof value === "string" || typeof value === "number" ? String(value) : fallback;

export function AdminPipelineDrawer({ conversation, open, onClose }) {
  const [selectedMessageId, setSelectedMessageId] = useState(null);
  const messages = useMemo(() => Array.isArray(conversation?.messages) ? conversation.messages : [], [conversation]);
  const selectedMessage = messages.find((message) => message?.id === selectedMessageId);

  useEffect(() => {
    setSelectedMessageId(messages.find((message) => message?.role === "assistant" && message?.debug)?.id || null);
  }, [conversation, messages]);

  if (!open || !conversation) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-carbon-950/55" role="dialog" aria-modal="true" aria-labelledby="admin-pipeline-title">
      <section className="flex h-full w-full max-w-3xl flex-col bg-canvas-100 shadow-lift">
        <header className="flex items-start justify-between border-b border-carbon-950 bg-canvas-50 px-5 py-5 sm:px-7">
          <div className="min-w-0"><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-vermilion-600">Operator ledger / conversation</p><h2 id="admin-pipeline-title" className="mt-1 truncate font-display text-3xl">{textOf(conversation.title, "Untitled conversation")}</h2><p className="mt-1 font-mono text-[9px] uppercase tracking-[0.12em] text-carbon-500">{textOf(conversation.user_email || conversation.owner_email, "Unassigned owner")}</p></div>
          <button type="button" aria-label="Close conversation details" onClick={onClose} className="flex h-10 w-10 shrink-0 items-center justify-center border border-carbon-950 text-carbon-500 hover:bg-carbon-950 hover:text-canvas-50 focus-visible:outline-none"><X size={17} aria-hidden="true" /></button>
        </header>
        <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(15rem,0.8fr)_minmax(0,1.2fr)]">
          <div className="min-h-0 overflow-y-auto border-b border-carbon-950 bg-canvas-50 p-4 lg:border-b-0 lg:border-r">
            <div className="mb-4 flex items-center gap-2"><MessageSquare size={14} className="text-vermilion-500" aria-hidden="true" /><p className="font-mono text-[9px] uppercase tracking-[0.18em] text-carbon-500">Messages / {messages.length}</p></div>
            <div className="space-y-2">{messages.length ? messages.map((message, index) => { const assistant = message?.role === "assistant"; const hasTrace = Boolean(message?.debug || message?.debug_trace); return <article key={message?.id || index} className={`border-l-2 ${selectedMessageId === message?.id ? "border-vermilion-500" : "border-canvas-300"}`}><button type="button" onClick={() => assistant && hasTrace && setSelectedMessageId(message.id)} disabled={!assistant || !hasTrace} className={`w-full px-3 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-vermilion-500 ${assistant && hasTrace ? "hover:bg-canvas-100" : "cursor-default"}`}><div className="flex items-center justify-between gap-2"><span className="font-mono text-[9px] uppercase tracking-[0.12em] text-carbon-500">{assistant ? "Assistant" : "User"}</span>{assistant && hasTrace && <Activity size={13} className="text-moss-500" aria-label="Trace available" />}</div><p className="mt-2 line-clamp-4 break-words text-xs leading-5 text-carbon-700">{textOf(message?.content, "Empty message")}</p></button></article>; }) : <p className="border border-dashed border-canvas-300 px-3 py-5 text-xs text-carbon-500">No messages were returned for this conversation.</p>}</div>
          </div>
          <div className="min-h-0 overflow-hidden bg-carbon-950">{selectedMessage ? <DebugPanel debug={selectedMessage.debug || selectedMessage.debug_trace} onClose={() => setSelectedMessageId(null)} /> : <div className="grid h-full place-items-center px-6 text-center text-canvas-500"><div><Activity size={26} className="mx-auto mb-4 text-vermilion-400" aria-hidden="true" /><p className="font-display text-2xl text-canvas-50">Select an assistant trace</p><p className="mt-2 max-w-xs text-xs leading-5">Messages with a stored retrieval trace can be inspected here.</p></div></div>}</div>
        </div>
      </section>
    </div>
  );
}

