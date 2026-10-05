import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "secondary" | "success" | "warning" | "danger" | "outline" | "accent" | "academic" | "neutral";
}

export function Badge({ className, variant = "default", children, ...props }: BadgeProps) {
  const variants = {
    default: "bg-zinc-800 text-zinc-300 border-zinc-700",
    secondary: "bg-zinc-900 text-zinc-400 border-zinc-800",
    neutral: "bg-zinc-900 text-zinc-400 border-zinc-800",
    success: "bg-emerald-950/70 text-emerald-300 border-emerald-800/60",
    warning: "bg-amber-950/70 text-amber-300 border-amber-800/60",
    danger: "bg-rose-950/70 text-rose-300 border-rose-800/60",
    outline: "border-zinc-750 text-zinc-300 bg-transparent",
    accent: "bg-blue-950/70 text-blue-300 border-blue-800/60",
    academic: "bg-blue-950/70 text-blue-300 border-blue-800/60",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border tracking-wide",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
