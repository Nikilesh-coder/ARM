"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { Button } from "@/components/ui/button";
import { CheckCircle2, AlertCircle, ArrowRight, RefreshCw } from "lucide-react";
import { supabase } from "@/lib/supabase";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // State: "authenticating" | "success" | "error"
  const [status, setStatus] = useState<"authenticating" | "success" | "error">("authenticating");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [userEmail, setUserEmail] = useState<string>("");
  const isProcessedRef = useRef(false);

  useEffect(() => {
    if (isProcessedRef.current) return;
    isProcessedRef.current = true;

    async function handleAuthCallback() {
      if (typeof window === "undefined") return;

      const hash = window.location.hash || "";
      const errorParam = searchParams.get("error");
      const errorDescription = searchParams.get("error_description");

      // 1. Check for error parameters in query string
      if (errorParam || errorDescription) {
        const decoded = decodeURIComponent(
          (errorDescription || errorParam || "Authentication with Google failed.").replace(/\+/g, " ")
        );
        setStatus("error");
        setErrorMessage(decoded);
        return;
      }

      // 2. Check for error in hash fragment
      if (hash.includes("error=")) {
        const hashParams = new URLSearchParams(hash.replace(/^#/, ""));
        const hashErr =
          hashParams.get("error_description") || hashParams.get("error") || "Authentication failed.";
        setStatus("error");
        setErrorMessage(decodeURIComponent(hashErr.replace(/\+/g, " ")));
        return;
      }

      // 3. PKCE code exchange flow (?code=...)
      const code = searchParams.get("code");
      if (code) {
        try {
          const { data, error } = await supabase.auth.exchangeCodeForSession(code);
          if (error) {
            throw error;
          }

          if (data?.session?.user) {
            const user = data.session.user;
            completeSuccessfulLogin(user);
            return;
          }
        } catch (exchangeErr: any) {
          console.warn("[Auth Callback] PKCE code exchange error:", exchangeErr);
          // If code exchange failed, try falling back to getSession() below
        }
      }

      // 4. Session detection via getSession (handles hash fragments or already restored sessions)
      try {
        const { data, error } = await supabase.auth.getSession();
        if (error) {
          throw error;
        }

        if (data?.session?.user) {
          completeSuccessfulLogin(data.session.user);
          return;
        }
      } catch (sessionErr: any) {
        console.warn("[Auth Callback] Session retrieval error:", sessionErr);
      }

      // 5. Fallback: Listen for onAuthStateChange for up to 5 seconds
      const timeoutTimer = setTimeout(() => {
        if (status === "authenticating") {
          setStatus("error");
          setErrorMessage(
            "Authentication timed out or no active session was found. Please try signing in again."
          );
        }
      }, 5000);

      const {
        data: { subscription },
      } = supabase.auth.onAuthStateChange((event, newSession) => {
        if (event === "SIGNED_IN" && newSession?.user) {
          clearTimeout(timeoutTimer);
          completeSuccessfulLogin(newSession.user);
          subscription.unsubscribe();
        }
      });
    }

    function completeSuccessfulLogin(user: any) {
      const email = user.email || "";
      setUserEmail(email);

      // Resolve display name
      const metaName = user.user_metadata?.full_name || user.user_metadata?.name;
      let nameToUse = metaName && typeof metaName === "string" ? metaName.trim() : "";
      if (!nameToUse && email) {
        const prefix = email.split("@")[0].replace(/[._-]/g, " ");
        nameToUse = prefix.charAt(0).toUpperCase() + prefix.slice(1);
      }
      if (!nameToUse) {
        nameToUse = "Scholar";
      }

      // Sync to localStorage for ARM workspace and API clients
      if (typeof window !== "undefined") {
        localStorage.setItem("arm_user_name", nameToUse);
        if (email) localStorage.setItem("arm_user_email", email);
        if (user.id) localStorage.setItem("arm_user_id", user.id);

        // Clear query/hash parameters from URL without page reload
        if (window.history && window.history.replaceState) {
          window.history.replaceState({}, document.title, window.location.pathname);
        }
      }

      setStatus("success");

      // Smooth transition to ARM dashboard
      setTimeout(() => {
        router.replace("/app");
      }, 600);
    }

    handleAuthCallback();
  }, [searchParams, router, status]);

  return (
    <div className="min-h-screen bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 flex flex-col justify-between transition-colors duration-300">
      <PublicNav />

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-8 sm:p-10 shadow-xl dark:shadow-2xl space-y-6 text-center transition-colors duration-300">
            {/* Logo */}
            <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-700 flex items-center justify-center text-white font-mono font-bold text-base mx-auto shadow-xl">
              ARM
            </div>

            {/* STATE 1: Authenticating / Exchanging tokens */}
            {status === "authenticating" && (
              <div className="space-y-4 py-4 animate-in fade-in duration-300">
                <div className="flex justify-center">
                  <div className="relative flex items-center justify-center">
                    <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
                  </div>
                </div>
                <h1 className="text-xl font-semibold text-zinc-900 dark:text-white tracking-tight">
                  Signing in with Google...
                </h1>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-xs mx-auto leading-relaxed">
                  Verifying your Google authentication and establishing a secure session with ARM.
                </p>
              </div>
            )}

            {/* STATE 2: Success */}
            {status === "success" && (
              <div className="space-y-4 py-4 animate-in fade-in zoom-in-95 duration-300">
                <div className="flex justify-center">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/10 dark:bg-emerald-500/20 flex items-center justify-center text-emerald-500 border border-emerald-500/30">
                    <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                  </div>
                </div>
                <h1 className="text-xl font-semibold text-zinc-900 dark:text-white tracking-tight">
                  Welcome to ARM!
                </h1>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  Signed in as <span className="font-semibold text-zinc-700 dark:text-zinc-300">{userEmail}</span>.
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">
                  Redirecting to your workspace...
                </p>
              </div>
            )}

            {/* STATE 3: Error */}
            {status === "error" && (
              <div className="space-y-4 py-2 animate-in fade-in duration-300">
                <div className="flex justify-center">
                  <div className="w-12 h-12 rounded-full bg-red-500/10 dark:bg-red-500/20 flex items-center justify-center text-red-500 border border-red-500/30">
                    <AlertCircle className="w-6 h-6 text-red-500" />
                  </div>
                </div>
                <h1 className="text-xl font-semibold text-zinc-900 dark:text-white tracking-tight">
                  Authentication Failed
                </h1>
                <div className="p-3.5 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 text-xs text-red-700 dark:text-red-300 text-left space-y-1">
                  <p className="font-medium">Error Details:</p>
                  <p className="text-[11px] leading-relaxed break-words opacity-90">
                    {errorMessage || "Unable to complete Google authentication."}
                  </p>
                </div>
                <div className="pt-2">
                  <Link href="/login" className="block">
                    <Button variant="primary" size="lg" className="w-full text-xs font-semibold">
                      Return to Sign In <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <React.Suspense
      fallback={
        <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6">
          <div className="flex flex-col items-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-700 flex items-center justify-center text-white font-mono font-bold text-base shadow-xl">
              ARM
            </div>
            <p className="text-sm text-zinc-400 font-light flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              Completing secure login...
            </p>
          </div>
        </div>
      }
    >
      <AuthCallbackContent />
    </React.Suspense>
  );
}
