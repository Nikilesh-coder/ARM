"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

interface PersonalizedWelcomeProps {
  userName?: string;
  destinationUrl?: string;
  onFinished?: () => void;
}

export function PersonalizedWelcome({
  userName,
  destinationUrl = "/app",
  onFinished,
}: PersonalizedWelcomeProps) {
  const router = useRouter();
  const displayName = userName && userName.trim().length > 0 ? userName.trim() : "there";

  const [isRevealed, setIsRevealed] = useState(false);
  const [isFadingOut, setIsFadingOut] = useState(false);
  const [isReducedMotion, setIsReducedMotion] = useState(false);

  useEffect(() => {
    // Check user preference for reduced motion
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) {
      setIsReducedMotion(true);
      setIsRevealed(true);
      const timer = setTimeout(() => {
        setIsFadingOut(true);
        setTimeout(() => {
          if (onFinished) onFinished();
          else router.push(destinationUrl);
        }, 400);
      }, 1000);
      return () => clearTimeout(timer);
    }

    // Trigger the smooth mask + upward reveal shortly after mount
    const revealTimer = setTimeout(() => {
      setIsRevealed(true);
    }, 100);

    // Keep visible briefly, then smoothly transition into ARM dashboard
    const exitTimer = setTimeout(() => {
      setIsFadingOut(true);
      setTimeout(() => {
        if (onFinished) onFinished();
        else router.push(destinationUrl);
      }, 500);
    }, 1800);

    return () => {
      clearTimeout(revealTimer);
      clearTimeout(exitTimer);
    };
  }, [destinationUrl, onFinished, router]);

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex flex-col items-center justify-center bg-black transition-opacity duration-500 select-none",
        isFadingOut ? "opacity-0 pointer-events-none" : "opacity-100"
      )}
    >
      {/* Subtle ambient lighting */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[450px] h-[450px] bg-zinc-900/30 rounded-full blur-[140px] pointer-events-none" />

      <div className="relative z-10 text-center px-6 max-w-2xl mx-auto">
        <p className="text-xs uppercase tracking-[0.35em] text-zinc-500 font-mono mb-4">
          ARM Workspace Initializing
        </p>

        {/* Masked Container for Upward Text Reveal (NOT a typewriter) */}
        <div className="overflow-hidden py-3">
          <h1
            className={cn(
              "text-4xl sm:text-6xl md:text-7xl font-extralight text-white tracking-tight leading-tight transition-all duration-900 ease-out transform",
              isReducedMotion || isRevealed
                ? "translate-y-0 opacity-100 filter-none"
                : "translate-y-full opacity-0 blur-[3px]"
            )}
          >
            Hello, <span className="font-medium text-white">{displayName}</span>
          </h1>
        </div>

        {/* Subtitle smoothly reveals alongside */}
        <div className="overflow-hidden py-1 mt-3">
          <p
            className={cn(
              "text-xs sm:text-sm text-zinc-400 font-light transition-all duration-800 delay-200 ease-out transform",
              isReducedMotion || isRevealed
                ? "translate-y-0 opacity-100"
                : "translate-y-6 opacity-0"
            )}
          >
            Preparing your college templates and project evidence...
          </p>
        </div>
      </div>
    </div>
  );
}

export const ArmPersonalizedWelcome = PersonalizedWelcome;
