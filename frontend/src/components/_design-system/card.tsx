// Card primitive — surface for grouping content. No internal state.
// Usage:
//   <Card><CardHeader title="Workspace" subtitle="prod"/><CardBody>...</CardBody></Card>

import { forwardRef, type HTMLAttributes, type ReactNode } from "react";
import { cn } from "./lib/cn";

export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("rounded-lg border border-zinc-800 bg-zinc-900", className)}
      {...props}
    />
  )
);
Card.displayName = "Card";

interface CardHeaderProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}

export function CardHeader({ title, subtitle, actions, className, ...props }: CardHeaderProps) {
  return (
    <div
      className={cn("flex items-center justify-between gap-4 border-b border-zinc-800 px-6 py-4", className)}
      {...props}
    >
      <div className="min-w-0">
        <h3 className="text-sm font-medium text-zinc-100 truncate">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-zinc-400 truncate">{subtitle}</p>}
      </div>
      {actions && <div className="shrink-0 flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function CardBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-6", className)} {...props} />;
}

export function CardFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("flex items-center justify-end gap-2 border-t border-zinc-800 px-6 py-3", className)} {...props} />
  );
}
