// Input primitive — text input matching design system tokens.
// Usage:
//   <Input type="email" placeholder="you@example.com" />
//   <Input invalid aria-invalid="true" />

import { forwardRef, type InputHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "./lib/cn";

const inputVariants = cva(
  "w-full rounded-md border bg-zinc-900 px-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-zinc-950 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150",
  {
    variants: {
      size: {
        sm: "h-8 text-xs",
        md: "h-9",
        lg: "h-10",
      },
      invalid: {
        true: "border-red-500/50 focus:border-red-500 focus:ring-red-500",
        false: "border-zinc-800 focus:border-blue-500 focus:ring-blue-500",
      },
    },
    defaultVariants: { size: "md", invalid: false },
  }
);

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size">,
    VariantProps<typeof inputVariants> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, size, invalid, ...props }, ref) => (
    <input ref={ref} className={cn(inputVariants({ size, invalid }), className)} {...props} />
  )
);
Input.displayName = "Input";
