"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { PersonalizedWelcome } from "@/components/arm/personalized-welcome";
import { Button } from "@/components/ui/button";
import { StatusBanner } from "@/components/ui/status-banner";
import { Lock, Mail, User, ArrowRight, CheckCircle2, RefreshCw, AlertCircle } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/lib/auth-context";

export default function SignupPage() {
  const router = useRouter();
  const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showPersonalizedWelcome, setShowPersonalizedWelcome] = useState(false);

  // Email confirmation state
  const [isPendingConfirmation, setIsPendingConfirmation] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendMessage, setResendMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);

  // In-flight submission lock to prevent multi-click races
  const isSubmittingRef = React.useRef(false);

  useEffect(() => {
    if (!isAuthLoading && isAuthenticated && !showPersonalizedWelcome && !isPendingConfirmation) {
      router.replace("/app");
    }
  }, [isAuthLoading, isAuthenticated, showPersonalizedWelcome, isPendingConfirmation, router]);

  // Cooldown countdown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmittingRef.current || isLoading) return;

    setValidationError(null);
    setAuthError(null);

    // Strict validation
    if (!fullName.trim() || !email.trim() || !password || !confirmPassword) {
      setValidationError("All registration fields are required.");
      return;
    }

    if (!email.includes("@") || !email.includes(".")) {
      setValidationError("Please provide a valid academic email address.");
      return;
    }

    if (password.length < 8) {
      setValidationError("Password must contain at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setValidationError("Passwords do not match. Please re-enter.");
      return;
    }

    const cleanEmail = email.trim().toLowerCase();

    // Prevent rapid duplicate submissions for the same email within 30 seconds
    if (typeof window !== "undefined") {
      const lastAttempt = sessionStorage.getItem(`arm_signup_attempt_${cleanEmail}`);
      if (lastAttempt) {
        const elapsed = (Date.now() - parseInt(lastAttempt, 10)) / 1000;
        if (elapsed < 30) {
          setValidationError(`A signup request for ${cleanEmail} was submitted just moments ago. Please check your inbox or wait ${Math.ceil(30 - elapsed)}s.`);
          return;
        }
      }
    }

    isSubmittingRef.current = true;
    setIsLoading(true);

    try {
      if (typeof window !== "undefined") {
        sessionStorage.setItem(`arm_signup_attempt_${cleanEmail}`, Date.now().toString());
      }

      // Connect to Supabase Auth
      const { data, error } = await supabase.auth.signUp({
        email: cleanEmail,
        password: password,
        options: {
          data: {
            full_name: fullName.trim(),
          },
        },
      });

      if (error) {
        throw error;
      }

      // Persist profile name for workspace greeting and sidebar
      if (typeof window !== "undefined") {
        localStorage.setItem("arm_user_name", fullName.trim());
        localStorage.setItem("arm_user_email", cleanEmail);
        if (data?.user?.id) {
          localStorage.setItem("arm_user_id", data.user.id);
        }
      }

      // Check whether email confirmation is required (session is null when unconfirmed)
      if (data?.session) {
        // Direct session granted (auto-confirm enabled or dev)
        setShowPersonalizedWelcome(true);
      } else {
        // Email verification required
        setSubmittedEmail(cleanEmail);
        setIsPendingConfirmation(true);
        setResendCooldown(60); // Start 60-second cooldown
      }
    } catch (err: any) {
      const msg = err?.message || "";
      if (msg.toLowerCase().includes("rate limit") || err?.code === "over_email_send_rate_limit" || err?.status === 429) {
        setAuthError(
          "Email rate limit exceeded by Supabase. A verification email may already be on its way. Please check your inbox and spam folder, or wait a few minutes before trying again."
        );
      } else if (msg.toLowerCase().includes("already registered") || msg.toLowerCase().includes("user already exists")) {
        setAuthError("An account with this email address already exists. Please sign in or use forgot password.");
      } else if (msg.toLowerCase().includes("only request this after")) {
        setAuthError(msg);
      } else {
        setAuthError(msg || "Failed to create account. Please try again.");
      }
    } finally {
      setIsLoading(false);
      isSubmittingRef.current = false;
    }
  };

  const handleResendConfirmation = async () => {
    if (resendCooldown > 0 || resendLoading || !submittedEmail) return;

    setResendLoading(true);
    setResendMessage(null);

    try {
      const { error } = await supabase.auth.resend({
        type: "signup",
        email: submittedEmail,
      });

      if (error) {
        throw error;
      }

      setResendCooldown(60);
      setResendMessage({
        type: "success",
        text: `Verification email resent to ${submittedEmail}. Please check your inbox.`,
      });
    } catch (err: any) {
      const msg = err?.message || "";
      if (msg.toLowerCase().includes("rate limit") || err?.code === "over_email_send_rate_limit" || err?.status === 429) {
        setResendMessage({
          type: "error",
          text: "Email rate limit exceeded. Please wait a few minutes before requesting another email, or check your spam folder.",
        });
        setResendCooldown(120);
      } else {
        setResendMessage({
          type: "error",
          text: msg || "Unable to resend email right now. Please wait a moment and try again.",
        });
      }
    } finally {
      setResendLoading(false);
    }
  };

  if (showPersonalizedWelcome) {
    return <PersonalizedWelcome userName={fullName} destinationUrl="/app" />;
  }

  // View: Pending Email Confirmation
  if (isPendingConfirmation) {
    return (
      <div className="min-h-screen bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 flex flex-col justify-between transition-colors duration-300">
        <PublicNav />
        <main className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-md">
            <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-8 sm:p-10 shadow-xl dark:shadow-2xl space-y-6 text-center">
              <div className="w-14 h-14 rounded-2xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800/60 flex items-center justify-center text-blue-600 dark:text-blue-400 mx-auto shadow-sm">
                <Mail className="w-7 h-7" />
              </div>

              <div className="space-y-2">
                <h1 className="text-2xl font-semibold text-zinc-900 dark:text-white tracking-tight">
                  Verify Your Academic Email
                </h1>
                <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                  We sent an account activation link to:
                </p>
                <div className="inline-block px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-mono font-medium text-zinc-900 dark:text-zinc-200 break-all">
                  {submittedEmail}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800/80 text-left space-y-2 text-xs text-zinc-600 dark:text-zinc-400">
                <p className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  <span>Click the link in the email to activate your account.</span>
                </p>
                <p className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                  <span>If you don&apos;t see the email, check your spam/junk folder.</span>
                </p>
              </div>

              {resendMessage && (
                <StatusBanner
                  type={resendMessage.type === "success" ? "success" : "error"}
                  title={resendMessage.type === "success" ? "Email Resent" : "Rate Limit Notice"}
                  message={resendMessage.text}
                />
              )}

              <div className="space-y-3 pt-2">
                <Button
                  type="button"
                  variant="primary"
                  size="lg"
                  className="w-full text-xs font-semibold"
                  onClick={() => router.push("/login")}
                >
                  Proceed to Sign In <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                </Button>

                <button
                  type="button"
                  disabled={resendCooldown > 0 || resendLoading}
                  onClick={handleResendConfirmation}
                  className="w-full text-xs text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 py-2 transition-colors"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${resendLoading ? "animate-spin" : ""}`} />
                  {resendCooldown > 0
                    ? `Resend available in ${resendCooldown}s`
                    : resendLoading
                    ? "Sending..."
                    : "Resend verification email"}
                </button>
              </div>
            </div>
          </div>
        </main>
        <PublicFooter />
      </div>
    );
  }

  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-700 flex items-center justify-center text-white font-mono font-bold text-base shadow-xl">
            ARM
          </div>
          <p className="text-sm text-zinc-400 font-light flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            Checking session...
          </p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 flex flex-col justify-between transition-colors duration-300">
      <PublicNav />

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-8 sm:p-10 shadow-xl dark:shadow-2xl space-y-6 transition-colors duration-300">
            <div className="text-center space-y-2">
              <div className="w-10 h-10 rounded-xl bg-zinc-900 border border-zinc-750 flex items-center justify-center text-white font-mono font-bold text-sm mx-auto mb-2 shadow-xs">
                ARM
              </div>
              <h1 className="text-2xl font-semibold text-zinc-900 dark:text-white tracking-tight">
                Create Your Account
              </h1>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Join ARM to synthesize academic project and seminar documentation
              </p>
            </div>

            {/* Validation / Auth Alerts */}
            {validationError && (
              <StatusBanner
                type="warning"
                title="Validation Error"
                message={validationError}
              />
            )}

            {authError && (
              <StatusBanner
                type="error"
                title="Registration Error"
                message={authError}
              />
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-zinc-500" />
                  Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. SaiNikilesh"
                  disabled={isLoading}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 text-sm text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-600 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-zinc-500" />
                  Academic Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="scholar@university.edu"
                  disabled={isLoading}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 text-sm text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-600 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-zinc-500" />
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  disabled={isLoading}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 text-sm text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-600 transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-zinc-500" />
                  Confirm Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter your password"
                  disabled={isLoading}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 text-sm text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-600 transition-colors"
                />
              </div>

              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={isLoading}
                className="w-full text-xs font-semibold mt-2"
              >
                Create Account <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
              </Button>
            </form>

            <div className="pt-4 border-t border-zinc-200 dark:border-zinc-900 text-center text-xs text-zinc-500 dark:text-zinc-400">
              Already have an account?{" "}
              <Link href="/login" className="text-zinc-900 dark:text-white font-semibold hover:underline">
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
