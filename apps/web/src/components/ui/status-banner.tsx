import React from "react";
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatusBannerProps {
  type?: "info" | "success" | "warning" | "error";
  title: string;
  message?: string;
  actionText?: string;
  onAction?: () => void;
  className?: string;
}

export function StatusBanner({
  type = "info",
  title,
  message,
  actionText,
  onAction,
  className,
}: StatusBannerProps) {
  const configs = {
    info: {
      bg: "bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-900/60 text-blue-900 dark:text-blue-200",
      icon: Info,
      iconColor: "text-blue-500 dark:text-blue-400",
    },
    success: {
      bg: "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-900/60 text-emerald-900 dark:text-emerald-200",
      icon: CheckCircle2,
      iconColor: "text-emerald-500 dark:text-emerald-400",
    },
    warning: {
      bg: "bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-900/60 text-amber-900 dark:text-amber-200",
      icon: AlertTriangle,
      iconColor: "text-amber-500 dark:text-amber-400",
    },
    error: {
      bg: "bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-900/60 text-rose-900 dark:text-rose-200",
      icon: AlertCircle,
      iconColor: "text-rose-500 dark:text-rose-400",
    },
  };

  const { bg, icon: Icon, iconColor } = configs[type];

  return (
    <div
      className={cn(
        "p-4 rounded-xl border flex items-start gap-3.5 text-sm transition-all shadow-xs",
        bg,
        className
      )}
      role="alert"
    >
      <Icon className={cn("w-5 h-5 shrink-0 mt-0.5", iconColor)} />
      <div className="flex-1">
        <h4 className="font-medium text-zinc-900 dark:text-white">{title}</h4>
        {message && <p className="text-zinc-600 dark:text-zinc-300 text-xs mt-0.5 leading-relaxed">{message}</p>}
      </div>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="text-xs font-semibold underline underline-offset-4 hover:opacity-80 shrink-0 self-center"
        >
          {actionText}
        </button>
      )}
    </div>
  );
}
