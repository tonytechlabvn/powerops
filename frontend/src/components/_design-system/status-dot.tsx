// StatusDot — small colored dot for status pills. Pairs with Badge or text label.
// Usage:
//   <StatusDot intent="success" />
//   <StatusDot intent="warning" pulse />

import type { HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "./lib/cn";

const dotVariants = cva("inline-block h-2 w-2 rounded-full", {
  variants: {
    intent: {
      neutral: "bg-zinc-500",
      primary: "bg-blue-500",
      success: "bg-emerald-500",
      warning: "bg-amber-500",
      danger: "bg-red-500",
      info: "bg-sky-500",
    },
    pulse: { true: "animate-pulse", false: "" },
  },
  defaultVariants: { intent: "neutral", pulse: false },
});

export interface StatusDotProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof dotVariants> {}

export function StatusDot({ className, intent, pulse, ...props }: StatusDotProps) {
  return <span aria-hidden="true" className={cn(dotVariants({ intent, pulse }), className)} {...props} />;
}
