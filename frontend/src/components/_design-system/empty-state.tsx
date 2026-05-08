// EmptyState — shown when a list/page has no data. Encourages a primary action.
// Usage:
//   <EmptyState
//     icon={<FolderOpen className="h-6 w-6"/>}
//     title="No workspaces yet"
//     description="Create your first workspace to get started."
//     action={<Button>New workspace</Button>}
//   />

import type { ReactNode } from "react";
import { cn } from "./lib/cn";

interface EmptyStateProps {
  icon?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-zinc-800 bg-zinc-900/50 px-6 py-12 text-center",
        className
      )}
    >
      {icon && (
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800/60 text-zinc-400">
          {icon}
        </div>
      )}
      <div>
        <h3 className="text-sm font-medium text-zinc-100">{title}</h3>
        {description && <p className="mt-1 text-xs text-zinc-400 max-w-sm">{description}</p>}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
