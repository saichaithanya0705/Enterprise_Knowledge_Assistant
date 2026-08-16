export function Badge({ children, tone = "neutral" }) {
  const tones = {
    neutral: "bg-canvas-200 text-carbon-500 border-canvas-300",
    amber: "bg-[#F5E7C9] text-[#8C641D] border-[#D9B872]",
    teal: "bg-[#E3ECE4] text-moss-500 border-[#AFC1B1]",
    coral: "bg-[#F8E3DD] text-vermilion-600 border-[#E4A698]",
  };
  return (
    <span className={`inline-flex items-center gap-1 border px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.08em] ${tones[tone]}`}>
      {children}
    </span>
  );
}
