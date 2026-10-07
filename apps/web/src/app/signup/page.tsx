"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { PersonalizedWelcome } from "@/components/arm/personalized-welcome";
import { Button } from "@/components/ui/button";
import { StatusBanner } from "@/components/ui/status-banner";
import { Lock, Mail, User, ArrowRight } from "lucide-react";
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

  useEffect(() => {
    if (!isAuthLoading && isAuthenticated && !showPersonalizedWelcome) {
      router.replace("/app");
    }
  }, [isAuthLoading, isAuthenticated, showPersonalizedWelcome, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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

    setIsLoading(true);

    try {
      // Connect to Supabase Auth
      const { data, error } = await supabase.auth.signUp({
        email: email.trim(),
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
        localStorage.setItem("arm_user_email", email.trim());
        if (data?.user?.id) {
          localStorage.setItem("arm_user_id", data.user.id);
        }
      }

      // Trigger Personalized Typewriter Welcome before entering dashboard
      setShowPersonalizedWelcome(true);
    } catch (err: any) {
      setAuthError(err?.message || "Failed to create account. Please try again.");
      setIsLoading(false);
    }
  };

  if (showPersonalizedWelcome) {
    return <PersonalizedWelcome userName={fullName} destinationUrl="/app" />;
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
