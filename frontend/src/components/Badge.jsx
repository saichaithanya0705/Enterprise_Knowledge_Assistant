export function Badge({ children, tone = "neutral" }) {
  const tones = {
    neutral: "bg-ink-700 text-paper-300 border-ink-600",
    amber: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    teal: "bg-teal-500/10 text-teal-400 border-teal-500/30",
    coral: "bg-coral-500/10 text-coral-500 border-coral-500/30",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-mono ${tones[tone]}`}>
      {children}
    </span>
  );
}
