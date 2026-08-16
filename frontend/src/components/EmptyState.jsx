export function EmptyState({ icon: Icon, title, description, action, heading = "p" }) {
  const Heading = heading;
  return (
    <div className="relative mx-auto flex max-w-2xl flex-col items-start border-y border-carbon-950 px-1 py-12 text-left">
      <div className="flex items-start gap-5">
        {Icon && (
          <div className="flex h-12 w-12 shrink-0 items-center justify-center bg-carbon-950 text-canvas-50">
            <Icon size={20} aria-hidden="true" />
          </div>
        )}
        <div>
          <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.2em] text-vermilion-600">Archive note</p>
          <Heading className="font-display text-3xl leading-none text-carbon-950">{title}</Heading>
          {description && <p className="mt-3 max-w-md text-sm leading-6 text-carbon-500">{description}</p>}
          {action}
        </div>
      </div>
    </div>
  );
}
