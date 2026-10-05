import React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger" | "academic";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", isLoading = false, children, disabled, ...props }, ref) => {
    const base = "inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-zinc-400/30 disabled:opacity-40 disabled:pointer-events-none select-none";

    const variants = {
      primary: "bg-white text-black hover:bg-zinc-200 active:scale-[0.98] shadow-sm",
      secondary: "bg-zinc-800 text-zinc-100 hover:bg-zinc-700 active:scale-[0.98] border border-zinc-750",
      outline: "border border-zinc-800 bg-transparent text-zinc-300 hover:bg-zinc-900 hover:text-white active:scale-[0.98]",
      ghost: "text-zinc-400 hover:text-white hover:bg-zinc-900 active:scale-[0.98]",
      danger: "bg-rose-950 text-rose-200 border border-rose-900 hover:bg-rose-900 active:scale-[0.98]",
      academic: "bg-blue-600 text-white hover:bg-blue-500 active:scale-[0.98] shadow-sm border border-blue-500",
    };

    const sizes = {
      sm: "text-xs px-3 py-1.5 h-8 gap-1.5",
      md: "text-sm px-4 py-2 h-9 sm:h-10 gap-2",
      lg: "text-base px-6 py-2.5 h-11 sm:h-12 gap-2.5",
    };

    return (
      <button
        ref={ref}
        className={cn(base, variants[variant], sizes[size], className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && (
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
