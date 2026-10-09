"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { PersonalizedWelcome } from "@/components/arm/personalized-welcome";
import { Button } from "@/components/ui/button";
import { StatusBanner } from "@/components/ui/status-banner";
import { Lock, Mail, ArrowRight, RefreshCw, CheckCircle2, KeyRound, AlertCircle, X } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/lib/auth-context";

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showPersonalizedWelcome, setShowPersonalizedWelcome] = useState(false);
  const [resolvedName, setResolvedName] = useState("there");

  // Email verification required state
  const [isEmailUnconfirmed, setIsEmailUnconfirmed] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendMessage, setResendMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Forgot password modal state
  const [showForgotPasswordModal, setShowForgotPasswordModal] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetLoading, setResetLoading] = useState(false);
  const [resetCooldown, setResetCooldown] = useState(0);
  const [resetStatus, setResetStatus] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Password recovery mode (when user clicked reset link in email)
  const [isRecoveryMode, setIsRecoveryMode] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [recoveryLoading, setRecoveryLoading] = useState(false);
  const [recoveryError, setRecoveryError] = useState<string | null>(null);
  const [recoverySuccess, setRecoverySuccess] = useState(false);

  // Detect recovery mode or email confirmation in URL / hash
  useEffect(() => {
    if (typeof window !== "undefined") {
      const hash = window.location.hash || "";
      const type = searchParams.get("type");
      const errorDesc = searchParams.get("error_description");

      if (errorDesc) {
        setAuthError(decodeURIComponent(errorDesc.replace(/\+/g, " ")));
      } else if (searchParams.get("verified") === "true" || hash.includes("type=signup")) {
        setAuthSuccess("Your email address was successfully verified! You can now sign in.");
      }

      if (type === "recovery" || hash.includes("type=recovery")) {
        setIsRecoveryMode(true);
      }
    }
  }, [searchParams]);

  // Cooldown timer for resend verification
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Cooldown timer for reset password
  useEffect(() => {
    if (resetCooldown <= 0) return;
    const timer = setInterval(() => {
      setResetCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [resetCooldown]);

  useEffect(() => {
    if (!isAuthLoading && isAuthenticated && !showPersonalizedWelcome && !isRecoveryMode) {
      router.replace("/app");
    }
  }, [isAuthLoading, isAuthenticated, showPersonalizedWelcome, isRecoveryMode, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);
    setAuthError(null);
    setAuthSuccess(null);
    setIsEmailUnconfirmed(false);
    setResendMessage(null);

    // Validation
    if (!email.trim() || !password) {
      setValidationError("Please provide both your academic email and password.");
      return;
    }

    if (!email.includes("@") || !email.includes(".")) {
      setValidationError("Please enter a valid email address.");
      return;
    }

    setIsLoading(true);

    try {
      // Connect to Supabase Auth: signInWithPassword verifies credentials without sending an email
      const { data, error } = await supabase.auth.signInWithPassword({
        email: email.trim().toLowerCase(),
        password: password,
      });

      if (error) {
        throw error;
      }

      // Resolve user name dynamically from Supabase user_metadata, profiles, or email
      let nameToUse = data?.user?.user_metadata?.full_name || "Scholar";
      if (!nameToUse || nameToUse === "Scholar") {
        const prefix = email.split("@")[0].replace(/[._-]/g, " ");
        nameToUse = prefix.charAt(0).toUpperCase() + prefix.slice(1);
      }

      if (typeof window !== "undefined") {
        localStorage.setItem("arm_user_name", nameToUse);
        localStorage.setItem("arm_user_email", email.trim().toLowerCase());
        if (data?.user?.id) {
          localStorage.setItem("arm_user_id", data.user.id);
        }
      }

      setResolvedName(nameToUse);
      setShowPersonalizedWelcome(true);
    } catch (err: any) {
      const msg = err?.message || "";
      const code = err?.code || "";

      if (code === "email_not_confirmed" || msg.toLowerCase().includes("email not confirmed")) {
        setIsEmailUnconfirmed(true);
        setAuthError(
          "Email Not Verified: Please verify your academic email address before logging in. Check your inbox and spam folder for the activation link."
        );
      } else if (msg.toLowerCase().includes("invalid login credentials")) {
        setAuthError("Invalid credentials. Please verify your email and password.");
      } else if (msg.toLowerCase().includes("rate limit") || code === "over_email_send_rate_limit" || err?.status === 429) {
        setAuthError("Rate limit reached. Please wait a few moments before trying again.");
      } else {
        setAuthError(msg || "Invalid credentials. Please verify your email and password.");
      }
      setIsLoading(false);
    }
  };

  const handleResendVerification = async () => {
    if (resendCooldown > 0 || resendLoading || !email.trim()) return;

    setResendLoading(true);
    setResendMessage(null);

    try {
      const { error } = await supabase.auth.resend({
        type: "signup",
        email: email.trim().toLowerCase(),
      });

      if (error) {
        throw error;
      }

      setResendCooldown(60);
      setResendMessage({
        type: "success",
        text: `Verification email resent to ${email.trim()}. Please check your inbox and spam folder.`,
      });
    } catch (err: any) {
      const msg = err?.message || "";
      if (msg.toLowerCase().includes("rate limit") || err?.code === "over_email_send_rate_limit" || err?.status === 429) {
        setResendMessage({
          type: "error",
          text: "Email rate limit exceeded. Please wait a few minutes before requesting another email, or check your spam folder for your existing link.",
        });
        setResendCooldown(120);
      } else {
        setResendMessage({
          type: "error",
          text: msg || "Unable to resend verification email right now. Please wait a moment and try again.",
        });
      }
    } finally {
      setResendLoading(false);
    }
  };

  const handleSendPasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (resetCooldown > 0 || resetLoading || !resetEmail.trim()) return;

    if (!resetEmail.includes("@") || !resetEmail.includes(".")) {
      setResetStatus({ type: "error", text: "Please enter a valid email address." });
      return;
    }

    setResetLoading(true);
    setResetStatus(null);

    try {
      const redirectTo = typeof window !== "undefined"
        ? `${window.location.origin}/login?type=recovery`
        : undefined;

      const { error } = await supabase.auth.resetPasswordForEmail(resetEmail.trim().toLowerCase(), {
        redirectTo,
      });

      if (error) {
        throw error;
      }

      setResetCooldown(60);
      setResetStatus({
        type: "success",
        text: `Password reset instructions sent to ${resetEmail.trim()}. Check your inbox and click the link to reset your password.`,
      });
    } catch (err: any) {
      const msg = err?.message || "";
      if (msg.toLowerCase().includes("rate limit") || err?.code === "over_email_send_rate_limit" || err?.status === 429) {
        setResetStatus({
          type: "error",
          text: "Email rate limit exceeded. Please wait a few minutes before requesting another reset link, or check your spam folder.",
        });
        setResetCooldown(120);
      } else {
        setResetStatus({
          type: "error",
          text: msg || "Unable to send reset instructions. Please verify the email and try again.",
        });
      }
    } finally {
      setResetLoading(false);
    }
  };

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setRecoveryError(null);

    if (!newPassword || newPassword.length < 8) {
      setRecoveryError("New password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmNewPassword) {
      setRecoveryError("Passwords do not match. Please re-enter.");
      return;
    }

    setRecoveryLoading(true);

    try {
      const { error } = await supabase.auth.updateUser({
        password: newPassword,
      });

      if (error) {
        throw error;
      }

      setRecoverySuccess(true);
      setTimeout(() => {
        router.replace("/app");
      }, 2000);
    } catch (err: any) {
      setRecoveryError(err?.message || "Failed to update password. Please try again or request a new reset link.");
      setRecoveryLoading(false);
    }
  };

  const handleQuickDemoFill = (demoName: string) => {
    setEmail(`${demoName.toLowerCase()}@university.edu`);
    setPassword("AcademicReport2026!");
    if (typeof window !== "undefined") {
      localStorage.setItem("arm_user_name", demoName);
    }
    setValidationError(null);
    setAuthError(null);
    setIsEmailUnconfirmed(false);
  };

  if (showPersonalizedWelcome) {
    return <PersonalizedWelcome userName={resolvedName} destinationUrl="/app" />;
  }

  // View: Recovery Mode (Set New Password)
  if (isRecoveryMode) {
    return (
      <div className="min-h-screen bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 flex flex-col justify-between transition-colors duration-300">
        <PublicNav />
        <main className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-md">
            <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-8 sm:p-10 shadow-xl dark:shadow-2xl space-y-6">
              <div className="text-center space-y-2">
                <div className="w-12 h-12 rounded-2xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800/60 flex items-center justify-center text-blue-600 dark:text-blue-400 mx-auto shadow-sm">
                  <KeyRound className="w-6 h-6" />
                </div>
                <h1 className="text-2xl font-semibold text-zinc-900 dark:text-white tracking-tight">
                  Set New Password
                </h1>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  Enter your new academic account password
                </p>
              </div>

              {recoveryError && (
                <StatusBanner type="error" title="Reset Error" message={recoveryError} />
              )}

              {recoverySuccess ? (
                <div className="text-center space-y-3 py-4">
                  <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto animate-bounce" />
                  <p className="text-sm font-medium text-zinc-900 dark:text-white">
                    Password updated successfully!
                  </p>
                  <p className="text-xs text-zinc-500">Redirecting to workspace...</p>
                </div>
              ) : (
                <form onSubmit={handleUpdatePassword} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5 text-zinc-500" />
                      New Password
                    </label>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Minimum 8 characters"
                      disabled={recoveryLoading}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 text-sm text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-600 transition-colors"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5 text-zinc-500" />
                      Confirm New Password
                    </label>
                    <input
                      type="password"
                      value={confirmNewPassword}
                      onChange={(e) => setConfirmNewPassword(e.target.value)}
                      placeholder="Re-enter new password"
                      disabled={recoveryLoading}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 text-sm text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-600 transition-colors"
                    />
                  </div>

                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    isLoading={recoveryLoading}
                    className="w-full text-xs font-semibold mt-2"
                  >
                    Save New Password <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                  </Button>
                </form>
              )}
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
          {/* Card */}
          <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-8 sm:p-10 shadow-xl dark:shadow-2xl space-y-6 transition-colors duration-300">
            <div className="text-center space-y-2">
              <div className="w-10 h-10 rounded-xl bg-zinc-900 border border-zinc-750 flex items-center justify-center text-white font-mono font-bold text-sm mx-auto mb-2 shadow-xs">
                ARM
              </div>
              <h1 className="text-2xl font-semibold text-zinc-900 dark:text-white tracking-tight">
                Sign in to ARM
              </h1>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Access your college templates, project evidence, and reports
              </p>
            </div>

            {/* Success alert (e.g. from email verification link) */}
            {authSuccess && (
              <StatusBanner
                type="success"
                title="Verified"
                message={authSuccess}
              />
            )}

            {/* Validation / Auth Alerts */}
            {validationError && (
              <StatusBanner
                type="warning"
                title="Input Required"
                message={validationError}
              />
            )}

            {authError && (
              <StatusBanner
                type="error"
                title={isEmailUnconfirmed ? "Email Not Verified" : "Authentication Error"}
                message={authError}
              />
            )}

            {/* Unconfirmed Email Action Panel */}
            {isEmailUnconfirmed && (
              <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 space-y-2.5 text-xs text-amber-800 dark:text-amber-300">
                <p className="leading-relaxed">
                  Haven&apos;t received your verification link yet or did it expire?
                </p>
                <button
                  type="button"
                  disabled={resendCooldown > 0 || resendLoading}
                  onClick={handleResendVerification}
                  className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-medium text-xs flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <RefreshCw className={`w-3 h-3 ${resendLoading ? "animate-spin" : ""}`} />
                  {resendCooldown > 0
                    ? `Resend available in ${resendCooldown}s`
                    : resendLoading
                    ? "Sending..."
                    : "Resend verification email"}
                </button>
                {resendMessage && (
                  <p className={`text-[11px] ${resendMessage.type === "success" ? "text-emerald-700 dark:text-emerald-400 font-medium" : "text-red-700 dark:text-red-400"}`}>
                    {resendMessage.text}
                  </p>
                )}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
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
                <div className="flex justify-between items-center">
                  <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-zinc-500" />
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setResetEmail(email.trim());
                      setResetStatus(null);
                      setShowForgotPasswordModal(true);
                    }}
                    className="text-[11px] text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 underline underline-offset-4"
                  >
                    Forgot password?
                  </button>
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
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
                Sign In <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
              </Button>
            </form>

            {/* Quick Demo Fill Buttons for Testing */}
            <div className="pt-2 text-center space-y-1">
              <span className="text-[10px] text-zinc-500 uppercase tracking-wider block font-mono">Quick test presets:</span>
              <div className="flex justify-center gap-2">
                <button
                  type="button"
                  onClick={() => handleQuickDemoFill("SaiNikilesh")}
                  className="text-[11px] font-mono px-2 py-1 rounded bg-zinc-100 dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white border border-zinc-200 dark:border-zinc-800 transition-colors"
                >
                  SaiNikilesh
                </button>
                <button
                  type="button"
                  onClick={() => handleQuickDemoFill("Rahul")}
                  className="text-[11px] font-mono px-2 py-1 rounded bg-zinc-100 dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white border border-zinc-200 dark:border-zinc-800 transition-colors"
                >
                  Rahul
                </button>
              </div>
            </div>

            <div className="pt-4 border-t border-zinc-200 dark:border-zinc-900 text-center text-xs text-zinc-500 dark:text-zinc-400">
              Don&apos;t have an account?{" "}
              <Link href="/signup" className="text-zinc-900 dark:text-white font-semibold hover:underline">
                Sign up
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Forgot Password Modal */}
      {showForgotPasswordModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-6 sm:p-8 shadow-2xl space-y-5">
            <div className="flex justify-between items-start">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">
                  Reset Password
                </h2>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  Enter your registered academic email to receive reset instructions
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowForgotPasswordModal(false)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {resetStatus && (
              <StatusBanner
                type={resetStatus.type === "success" ? "success" : "error"}
                title={resetStatus.type === "success" ? "Reset Link Sent" : "Request Error"}
                message={resetStatus.text}
              />
            )}

            <form onSubmit={handleSendPasswordReset} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-zinc-500" />
                  Academic Email
                </label>
                <input
                  type="email"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  placeholder="scholar@university.edu"
                  disabled={resetLoading}
                  required
                  className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 text-sm text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-600 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-600 transition-colors"
                />
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="md"
                  onClick={() => setShowForgotPasswordModal(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  isLoading={resetLoading}
                  disabled={resetCooldown > 0}
                  className="text-xs"
                >
                  {resetCooldown > 0 ? `Wait ${resetCooldown}s` : "Send Reset Link"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      <PublicFooter />
    </div>
  );
}

export default function LoginPage() {
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
              Loading...
            </p>
          </div>
        </div>
      }
    >
      <LoginFormContent />
    </React.Suspense>
  );
}
