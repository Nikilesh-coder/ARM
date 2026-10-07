"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { PersonalizedWelcome } from "@/components/arm/personalized-welcome";
import { Button } from "@/components/ui/button";
import { StatusBanner } from "@/components/ui/status-banner";
import { Lock, Mail, ArrowRight } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showPersonalizedWelcome, setShowPersonalizedWelcome] = useState(false);
  const [resolvedName, setResolvedName] = useState("there");

  useEffect(() => {
    if (!isAuthLoading && isAuthenticated && !showPersonalizedWelcome) {
      router.replace("/app");
    }
  }, [isAuthLoading, isAuthenticated, showPersonalizedWelcome, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);
    setAuthError(null);

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
      // Connect to Supabase Auth
      const { data, error } = await supabase.auth.signInWithPassword({
        email: email.trim(),
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
        localStorage.setItem("arm_user_email", email.trim());
        if (data?.user?.id) {
          localStorage.setItem("arm_user_id", data.user.id);
        }
      }

      setResolvedName(nameToUse);
      setShowPersonalizedWelcome(true);
    } catch (err: any) {
      setAuthError(err?.message || "Invalid credentials. Please verify your email and password.");
      setIsLoading(false);
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
  };

  if (showPersonalizedWelcome) {
    return <PersonalizedWelcome userName={resolvedName} destinationUrl="/app" />;
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
                title="Authentication Error"
                message={authError}
              />
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
                    onClick={() => alert("Password reset link will be sent to your academic email when SMTP is active.")}
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

      <PublicFooter />
    </div>
  );
}
