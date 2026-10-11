"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { Button } from "@/components/ui/button";
import { CheckCircle2, AlertCircle, ArrowRight, RefreshCw, Mail } from "lucide-react";
import { supabase } from "@/lib/supabase";

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Verification status: "verifying" | "success" | "error"
  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [userEmail, setUserEmail] = useState<string>("");

  // Resend state for error scenarios
  const [resendEmail, setResendEmail] = useState<string>("");
  const [resendLoading, setResendLoading] = useState<boolean>(false);
  const [resendCooldown, setResendCooldown] = useState<number>(0);
  const [resendFeedback, setResendFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const verificationAttempted = useRef(false);

  // Cooldown countdown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  useEffect(() => {
    if (verificationAttempted.current) return;
    verificationAttempted.current = true;

    async function handleVerification() {
      if (typeof window === "undefined") return;

      const hash = window.location.hash || "";
      const search = window.location.search || "";
      const errorParam = searchParams.get("error");
      const errorDescription = searchParams.get("error_description");
      const errorCode = searchParams.get("error_code");

      // 1. Check if Supabase redirected with error parameters in query or hash
      if (errorParam || errorDescription) {
        const decoded = decodeURIComponent(
          (errorDescription || errorParam || "Email verification failed.").replace(/\+/g, " ")
        );
        setStatus("error");
        setErrorMessage(decoded);

        // Pre-fill email from localStorage if available
        const cachedEmail = localStorage.getItem("arm_user_email") || "";
        if (cachedEmail) {
          setResendEmail(cachedEmail);
        }
        return;
      }

      // Check hash for error parameters (Supabase sometimes puts errors in hash fragment)
      if (hash.includes("error=")) {
        const hashParams = new URLSearchParams(hash.replace(/^#/, ""));
        const hashErr = hashParams.get("error_description") || hashParams.get("error") || "Email verification failed.";
        setStatus("error");
        setErrorMessage(decodeURIComponent(hashErr.replace(/\+/g, " ")));

        const cachedEmail = localStorage.getItem("arm_user_email") || "";
        if (cachedEmail) {
          setResendEmail(cachedEmail);
        }
        return;
      }

      // 2. PKCE code exchange flow (e.g., ?code=...)
      const code = searchParams.get("code");
      if (code) {
        try {
          const { data, error } = await supabase.auth.exchangeCodeForSession(code);
          if (error) {
            throw error;
          }

          if (data?.user?.email) {
            setUserEmail(data.user.email);
          }

          // REQUIRE MANUAL LOGIN: Sign out the auto-established session
          // so user must enter their credentials on the login screen
          await supabase.auth.signOut();

          // Clear any tokens left in URL
          if (window.history && window.history.replaceState) {
            window.history.replaceState({}, document.title, window.location.pathname);
          }

          setStatus("success");
          return;
        } catch (err: any) {
          const msg = err?.message || "";
          setStatus("error");
          if (
            msg.toLowerCase().includes("expired") ||
            msg.toLowerCase().includes("invalid") ||
            msg.toLowerCase().includes("pkce")
          ) {
            setErrorMessage(
              "This verification link has expired or has already been used. Please request a new verification link below or sign in if you already verified."
            );
          } else {
            setErrorMessage(msg || "Unable to complete verification with this link.");
          }

          const cachedEmail = localStorage.getItem("arm_user_email") || "";
          if (cachedEmail) {
            setResendEmail(cachedEmail);
          }
          return;
        }
      }

      // 3. Implicit hash flow (e.g., #access_token=...&type=signup)
      if (hash.includes("access_token") || hash.includes("type=signup")) {
        try {
          // Allow Supabase client detectSessionInUrl to parse the hash
          const { data } = await supabase.auth.getSession();
          if (data?.session?.user?.email) {
            setUserEmail(data.session.user.email);
          }

          // REQUIRE MANUAL LOGIN: Sign out the session immediately
          await supabase.auth.signOut();

          // Clean hash from URL bar to prevent token leakage
          if (window.history && window.history.replaceState) {
            window.history.replaceState({}, document.title, window.location.pathname);
          }

          setStatus("success");
          return;
        } catch (err: any) {
          console.warn("[VerifyEmail] Hash processing error:", err);
          setStatus("success"); // Still show verified since the token was present
          return;
        }
      }

      // 4. Fallback: Check if an active session already exists
      try {
        const { data } = await supabase.auth.getSession();
        if (data?.session?.user) {
          if (data.session.user.email) {
            setUserEmail(data.session.user.email);
          }
          // Enforce manual login
          await supabase.auth.signOut();
          setStatus("success");
          return;
        }
      } catch (err) {
        // Ignore session read error
      }

      // 5. If arrived with no code, no hash, and no active session
      const cachedEmail = localStorage.getItem("arm_user_email") || "";
      if (cachedEmail) {
        setResendEmail(cachedEmail);
      }
      setStatus("error");
      setErrorMessage(
        "No verification token found. Please click the activation link directly from your confirmation email."
      );
    }

    handleVerification();
  }, [searchParams]);

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (resendCooldown > 0 || resendLoading || !resendEmail.trim()) return;

    if (!resendEmail.includes("@") || !resendEmail.includes(".")) {
      setResendFeedback({ type: "error", text: "Please enter a valid email address." });
      return;
    }

    setResendLoading(true);
    setResendFeedback(null);

    try {
      const siteOrigin =
        typeof window !== "undefined"
          ? window.location.origin
          : (process.env.NEXT_PUBLIC_SITE_URL || "https://arm-app-2.vercel.app");
      const emailRedirectTo = `${siteOrigin}/verify-email`;

      const { error } = await supabase.auth.resend({
        type: "signup",
        email: resendEmail.trim().toLowerCase(),
        options: {
          emailRedirectTo,
        },
      });

      if (error) {
        throw error;
      }

      setResendCooldown(60);
      setResendFeedback({
        type: "success",
        text: `New verification link sent to ${resendEmail.trim()}. Please check your inbox and spam folder.`,
      });
    } catch (err: any) {
      const msg = err?.message || "";
      if (
        msg.toLowerCase().includes("rate limit") ||
        err?.code === "over_email_send_rate_limit" ||
        err?.status === 429
      ) {
        setResendFeedback({
          type: "error",
          text: "Email rate limit exceeded. Please wait a few minutes before requesting another verification email.",
        });
        setResendCooldown(120);
      } else {
        setResendFeedback({
          type: "error",
          text: msg || "Failed to resend verification email. Please try again in a few moments.",
        });
      }
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 flex flex-col justify-between transition-colors duration-300">
      <PublicNav />

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          {/* STATE 1: VERIFYING */}
          {status === "verifying" && (
            <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-8 sm:p-10 shadow-xl dark:shadow-2xl space-y-6 text-center">
              <div className="w-14 h-14 rounded-2xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800/60 flex items-center justify-center text-blue-600 dark:text-blue-400 mx-auto shadow-sm">
                <RefreshCw className="w-7 h-7 animate-spin" />
              </div>
              <div className="space-y-2">
                <h1 className="text-2xl font-semibold text-zinc-900 dark:text-white tracking-tight">
                  Verifying Your Email
                </h1>
                <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                  Securing your academic credentials and activating your ARM account...
                </p>
              </div>
            </div>
          )}

          {/* STATE 2: SUCCESS */}
          {status === "success" && (
            <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-8 sm:p-10 shadow-xl dark:shadow-2xl space-y-6 text-center animate-in fade-in duration-300">
              <div className="w-14 h-14 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mx-auto shadow-sm">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div className="space-y-2">
                <h1 className="text-2xl font-semibold text-zinc-900 dark:text-white tracking-tight">
                  Email Verified Successfully!
                </h1>
                <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                  Your account is ready. Please log in to continue.
                </p>
                {userEmail && (
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 pt-1">
                    Verified for: <span className="font-mono text-zinc-800 dark:text-zinc-200">{userEmail}</span>
                  </p>
                )}
              </div>

              <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800/80 text-left space-y-1.5 text-xs text-zinc-600 dark:text-zinc-400">
                <p className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                  <span>Academic profile activated.</span>
                </p>
                <p className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                  <span>Manual login required to ensure account security.</span>
                </p>
              </div>

              <div className="pt-2">
                <Button
                  type="button"
                  variant="primary"
                  size="lg"
                  className="w-full text-xs font-semibold py-3 shadow-md hover:shadow-lg transition-all"
                  onClick={() => router.push("/login?verified=true")}
                >
                  Go to Login <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </div>
          )}

          {/* STATE 3: ERROR / EXPIRED */}
          {status === "error" && (
            <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-8 sm:p-10 shadow-xl dark:shadow-2xl space-y-6 text-center animate-in fade-in duration-300">
              <div className="w-14 h-14 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 flex items-center justify-center text-amber-600 dark:text-amber-400 mx-auto shadow-sm">
                <AlertCircle className="w-8 h-8" />
              </div>

              <div className="space-y-2">
                <h1 className="text-2xl font-semibold text-zinc-900 dark:text-white tracking-tight">
                  Verification Link Notice
                </h1>
                <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                  {errorMessage || "This verification link could not be validated."}
                </p>
              </div>

              {resendFeedback && (
                <div
                  className={`p-3 rounded-lg text-xs text-left ${
                    resendFeedback.type === "success"
                      ? "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                      : "bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800"
                  }`}
                >
                  {resendFeedback.text}
                </div>
              )}

              {/* Resend Verification Form */}
              <form onSubmit={handleResend} className="space-y-3 pt-2 text-left">
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300">
                  Resend Verification Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="email"
                    value={resendEmail}
                    onChange={(e) => setResendEmail(e.target.value)}
                    placeholder="Enter your academic email"
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <Button
                  type="submit"
                  variant="outline"
                  size="md"
                  className="w-full text-xs font-medium"
                  isLoading={resendLoading}
                  disabled={resendCooldown > 0}
                >
                  {resendCooldown > 0 ? `Wait ${resendCooldown}s` : "Send New Verification Link"}
                </Button>
              </form>

              <div className="pt-2 border-t border-zinc-200 dark:border-zinc-800/80">
                <Button
                  type="button"
                  variant="primary"
                  size="md"
                  className="w-full text-xs font-semibold"
                  onClick={() => router.push("/login")}
                >
                  Go to Login <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}

export default function VerifyEmailPage() {
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
              Loading verification...
            </p>
          </div>
        </div>
      }
    >
      <VerifyEmailContent />
    </React.Suspense>
  );
}
