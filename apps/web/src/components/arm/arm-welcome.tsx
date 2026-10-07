"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowDown, Play } from "lucide-react";

interface ArmWelcomeProps {
  onContinue?: () => void;
}

export function ArmWelcome({ onContinue }: ArmWelcomeProps) {
  const fullText = "Hello, Welcome to ARM";
  const [displayedText, setDisplayedText] = useState("");
  const [isTypingComplete, setIsTypingComplete] = useState(false);
  const [showSupporting, setShowSupporting] = useState(false);
  const [showScrollPrompt, setShowScrollPrompt] = useState(false);
  const [isReducedMotion, setIsReducedMotion] = useState(false);

  useEffect(() => {
    // Check user preference for reduced motion
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mediaQuery.matches) {
      setIsReducedMotion(true);
      setDisplayedText(fullText);
      setIsTypingComplete(true);
      setShowSupporting(true);
      setShowScrollPrompt(true);
      return;
    }

    let currentIndex = 0;
    const typingInterval = setInterval(() => {
      if (currentIndex < fullText.length) {
        setDisplayedText(fullText.slice(0, currentIndex + 1));
        currentIndex++;
      } else {
        clearInterval(typingInterval);
        setIsTypingComplete(true);
        // After complete typing, briefly pause then reveal supporting description
        setTimeout(() => setShowSupporting(true), 400);
        setTimeout(() => setShowScrollPrompt(true), 900);
      }
    }, 55); // Smooth natural typing speed

    return () => clearInterval(typingInterval);
  }, []);

  const handleScrollToNext = () => {
    if (onContinue) {
      onContinue();
      return;
    }
    const nextEl = document.getElementById("arm-intro") || document.getElementById("theme-selection");
    if (nextEl) {
      nextEl.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section className="relative w-full min-h-screen bg-black flex flex-col items-center justify-center px-6 overflow-hidden select-none">
      {/* Subtle cinematic ambient spotlight */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] bg-zinc-900/30 rounded-full blur-[150px] pointer-events-none" />

      {/* Main Container */}
      <div className="relative z-10 text-center max-w-3xl mx-auto">
        <p className="text-xs uppercase tracking-[0.35em] text-zinc-500 font-mono mb-6">
          Academic Report Assistant
        </p>

        {/* Typewriter Header - Clean without cursor pipe symbol */}
        <h1 className="text-4xl sm:text-6xl md:text-7xl font-extralight text-white tracking-tight leading-tight min-h-[1.3em] flex items-center justify-center">
          <span>{displayedText}</span>
        </h1>

        {/* Supporting description appears smoothly after typing */}
        <div
          className={`transition-all duration-700 ease-out transform mt-6 ${
            showSupporting
              ? "opacity-100 translate-y-0"
              : "opacity-0 translate-y-3 pointer-events-none"
          }`}
        >
          <p className="text-base sm:text-lg text-zinc-400 font-light max-w-xl mx-auto leading-relaxed">
            Deterministic academic document generation crafted from your authentic evidence and college template.
          </p>

          <div className="mt-6 flex items-center justify-center gap-3">
            <Link
              href="/video"
              className="px-4 py-2 rounded-full bg-zinc-900/90 border border-zinc-750 text-xs font-mono text-zinc-300 hover:text-white hover:border-emerald-400/60 transition-all flex items-center gap-2 shadow-lg hover:scale-105"
            >
              <Play className="w-3.5 h-3.5 text-emerald-400 fill-emerald-400" />
              Watch Product Video (42s)
            </Link>
          </div>
        </div>
      </div>

      {/* Continue indicator / smooth scroll */}
      <div
        className={`absolute bottom-10 z-10 transition-all duration-700 ${
          showScrollPrompt ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2 pointer-events-none"
        }`}
      >
        <button
          onClick={handleScrollToNext}
          className="flex flex-col items-center gap-2 text-xs text-zinc-500 hover:text-zinc-300 transition-colors p-2 cursor-pointer"
          aria-label="Scroll to explore"
        >
          <span className="font-mono text-[11px] tracking-wider uppercase">Scroll to explore</span>
          <ArrowDown className="w-4 h-4 animate-bounce" />
        </button>
      </div>
    </section>
  );
}
