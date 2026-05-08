// Badge primitive — small status/tag indicator with semantic intents.
// Usage:
//   <Badge intent="success">Applied</Badge>
//   <Badge intent="warning">Drift</Badge>

import type { HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "./lib/cn";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
  {
    variants: {
      intent: {
        neutral: "bg-zinc-800/60 text-zinc-300 ring-zinc-700/50",
        primary: "bg-blue-500/10 text-blue-400 ring-blue-500/20",
        success: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20",
        warning: "bg-amber-500/10 text-amber-400 ring-amber-500/20",
        danger: "bg-red-500/10 text-red-400 ring-red-500/20",
        info: "bg-sky-500/10 text-sky-400 ring-sky-500/20",
      },
    },
    defaultVariants: { intent: "neutral" },
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, intent, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ intent }), className)} {...props} />;
}
