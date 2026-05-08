// IconButton — square button for icon-only actions. ARIA label REQUIRED.
// Usage:
//   <IconButton aria-label="Refresh"><RefreshCw className="h-4 w-4"/></IconButton>

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "./lib/cn";

const iconButtonVariants = cva(
  "inline-flex items-center justify-center rounded-md transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 disabled:opacity-50 disabled:pointer-events-none",
  {
    variants: {
      intent: {
        ghost: "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100",
        secondary: "border border-zinc-800 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100",
        danger: "text-zinc-400 hover:bg-red-500/10 hover:text-red-400",
      },
      size: {
        sm: "h-7 w-7",
        md: "h-8 w-8",
        lg: "h-9 w-9",
      },
    },
    defaultVariants: { intent: "ghost", size: "md" },
  }
);

export interface IconButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof iconButtonVariants> {
  "aria-label": string; // Required for icon-only buttons (a11y)
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, intent, size, type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(iconButtonVariants({ intent, size }), className)}
      {...props}
    />
  )
);
IconButton.displayName = "IconButton";
