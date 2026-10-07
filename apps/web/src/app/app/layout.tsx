"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function ProtectedAppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // While restoring session on app startup, show auth splash state
  // to avoid flashing unauthenticated or login screens
  if (isLoading) {
    return (
      <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6">
        <div className="flex flex-col items-center space-y-4">
          <div className="relative">
            <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-700 flex items-center justify-center text-white font-mono font-bold text-base shadow-xl">
              ARM
            </div>
            <div className="absolute -inset-1 rounded-2xl border border-blue-500/40 animate-ping pointer-events-none" />
          </div>
          <div className="flex flex-col items-center space-y-1.5 text-center">
            <span className="text-xs uppercase tracking-widest text-zinc-400 font-mono">
              Academic Report Assistant
            </span>
            <p className="text-sm text-zinc-300 font-light flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              Restoring secure session...
            </p>
          </div>
        </div>
      </div>
    );
  }

  // If not authenticated, render nothing while redirecting to /login
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
