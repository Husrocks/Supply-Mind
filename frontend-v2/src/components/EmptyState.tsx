import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
}

export function EmptyState({ icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-16 border border-hairline rounded-xl bg-canvas h-full w-full">
      <div className="mb-4 w-16 h-16 rounded-full bg-surface-strong flex items-center justify-center text-primary">
        {icon}
      </div>
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <p className="text-body mt-2 text-center max-w-md text-sm">{description}</p>
    </div>
  );
}
