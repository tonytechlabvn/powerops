// Skeleton — loading placeholder. Use for paragraph/avatar/row stand-ins.
// Usage:
//   <Skeleton className="h-4 w-32" />
//   <Skeleton variant="circle" className="h-8 w-8" />

import type { HTMLAttributes } from "react";
import { cn } from "./lib/cn";

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "rect" | "circle";
}

export function Skeleton({ className, variant = "rect", ...props }: SkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn(
        "animate-pulse bg-zinc-800/60",
        variant === "circle" ? "rounded-full" : "rounded-md",
        className
      )}
      {...props}
    />
  );
}
