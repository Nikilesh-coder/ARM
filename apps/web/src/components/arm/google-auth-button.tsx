"use client";

import React, { useState } from "react";
import { RefreshCw } from "lucide-react";
import { supabase } from "@/lib/supabase";

interface GoogleAuthButtonProps {
  mode?: "signin" | "signup";
  disabled?: boolean;
  onError?: (message: string) => void;
  className?: string;
}

export function GoogleIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
      />
    </svg>
  );
}

export function GoogleAuthButton({
  mode = "signin",
  disabled = false,
  onError,
  className = "",
}: GoogleAuthButtonProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleGoogleSignIn = async () => {
    if (disabled || isLoading) return;

    setIsLoading(true);
    try {
      const siteOrigin =
        typeof window !== "undefined"
          ? window.location.origin
          : (process.env.NEXT_PUBLIC_SITE_URL || "https://arm-caw2.vercel.app");
      const redirectTo = `${siteOrigin}/auth/callback`;

      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo,
          queryParams: {
            access_type: "offline",
            prompt: "select_account",
          },
        },
      });

      if (error) {
        throw error;
      }

      // If data.url is returned, navigate to it (Supabase typically handles this automatically in browser)
      if (data?.url && typeof window !== "undefined") {
        window.location.assign(data.url);
      }
    } catch (err: any) {
      console.error("[Auth] Google OAuth initialization error:", err);
      const msg =
        err?.message ||
        "Could not connect to Google authentication. Please ensure Google Sign-In is enabled in Supabase.";
      onError?.(msg);
      setIsLoading(false);
    }
  };

  const label =
    mode === "signup" ? "Continue with Google" : "Continue with Google";

  return (
    <button
      type="button"
      onClick={handleGoogleSignIn}
      disabled={disabled || isLoading}
      aria-label={label}
      className={`w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-sm font-medium text-zinc-700 dark:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-850 hover:border-zinc-300 dark:hover:border-zinc-700 active:scale-[0.99] transition-all shadow-xs disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer ${className}`}
    >
      {isLoading ? (
        <RefreshCw className="w-4 h-4 animate-spin text-zinc-500" />
      ) : (
        <GoogleIcon className="w-4 h-4 shrink-0" />
      )}
      <span>{isLoading ? "Connecting to Google..." : label}</span>
    </button>
  );
}
