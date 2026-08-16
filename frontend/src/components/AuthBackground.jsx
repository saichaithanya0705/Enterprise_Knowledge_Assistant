export function AuthBackground({ children, eyebrow = "Enterprise knowledge assistant" }) {
  return (
    <div className="relative min-h-[100dvh] overflow-hidden bg-canvas-100 text-carbon-950">
      <div className="pointer-events-none absolute inset-0 editorial-grid opacity-60" aria-hidden="true" />
      <div className="pointer-events-none absolute -right-24 top-16 h-72 w-72 border-[3rem] border-vermilion-500/10" aria-hidden="true" />
      <div className="pointer-events-none absolute -bottom-32 -left-24 h-96 w-96 border-[4rem] border-moss-500/10" aria-hidden="true" />
      <a href="#auth-main" className="fixed left-4 top-3 z-20 -translate-y-20 bg-carbon-950 px-4 py-2 text-sm font-semibold text-canvas-50 transition-transform focus:translate-y-0">Skip to form</a>
      <header className="relative z-10 flex items-center justify-between border-b border-carbon-950/15 px-5 py-5 sm:px-8">
        <p className="font-display text-xl tracking-tight">Knowledge<span className="text-vermilion-500">.</span>desk</p>
        <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-carbon-500">{eyebrow}</p>
      </header>
      <main id="auth-main" className="relative z-10 mx-auto grid min-h-[calc(100dvh-5rem)] w-full max-w-7xl items-center gap-10 px-5 py-12 sm:px-8 lg:grid-cols-[minmax(0,0.9fr)_minmax(22rem,32rem)] lg:gap-20 lg:py-16">
        <div className="hidden max-w-xl lg:block">
          <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-vermilion-600">Private workspace / access point</p>
          <h1 className="mt-5 font-display text-[clamp(3.5rem,7vw,7rem)] leading-[0.82] tracking-[-0.055em]">Answers with an <span className="italic text-vermilion-500">evidence trail.</span></h1>
          <p className="mt-8 max-w-md text-sm leading-7 text-carbon-500">Search the documents your team trusts, keep conversations private, and see the retrieval path behind every answer.</p>
        </div>
        <div className="w-full">{children}</div>
      </main>
    </div>
  );
}

