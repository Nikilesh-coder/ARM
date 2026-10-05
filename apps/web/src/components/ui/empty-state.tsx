import React from "react";
import { LucideIcon } from "lucide-react";
import { Button } from "./button";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon | React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
  children?: React.ReactNode;
}

export function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
  children,
}: EmptyStateProps) {
  const isComponent =
    typeof icon === "function" ||
    (typeof icon === "object" && icon !== null && !React.isValidElement(icon));
  const IconComponent = isComponent ? (icon as LucideIcon) : null;

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-xl border border-dashed border-zinc-300 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 transition-colors duration-200",
        className
      )}
    >
      {icon && (
        <div className="w-12 h-12 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center text-zinc-600 dark:text-zinc-400 mb-4 shadow-xs">
          {IconComponent ? <IconComponent className="w-6 h-6" /> : (icon as React.ReactNode)}
        </div>
      )}
      <h3 className="text-base font-semibold text-zinc-900 dark:text-white">{title}</h3>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-md mt-1 mb-6 leading-relaxed">
        {description}
      </p>
      {actionLabel && (
        <Button variant="primary" size="md" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
      {children}
    </div>
  );
}
