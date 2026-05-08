// Conditional className helper: clsx + tailwind-merge.
// Use everywhere primitives compose Tailwind utilities.

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
