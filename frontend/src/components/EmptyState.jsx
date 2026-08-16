export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center px-6">
      {Icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-ink-700 border border-ink-600">
          <Icon size={20} className="text-paper-500" />
        </div>
      )}
      <div>
        <p className="font-medium text-paper-100">{title}</p>
        {description && <p className="mt-1 text-sm text-paper-500 max-w-sm">{description}</p>}
      </div>
      {action}
    </div>
  );
}
