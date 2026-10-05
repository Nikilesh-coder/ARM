"use client";

import React, { useState, useEffect, useRef } from "react";
import { FolderGit2, FileCode2, Database, Cpu, FileCheck2, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

const HEADLINE_WORDS = ["Your", "AI", "Academic", "Report", "Assistant"];

const PIPELINE_STEPS = [
  {
    title: "Your Project",
    desc: "Define topic, scope, and objectives",
    icon: FolderGit2,
  },
  {
    title: "Your College Template",
    desc: "Upload official .docx format specification",
    icon: FileCode2,
  },
  {
    title: "Your Evidence",
    desc: "Attach code, datasets, plots & logs",
    icon: Database,
  },
  {
    title: "ARM AI",
    desc: "Synthesizes citations, sections & math",
    icon: Cpu,
  },
  {
    title: "Professional Report",
    desc: "Deterministic margins, typography & numbering",
    icon: FileCheck2,
  },
];

export function ArmIntro() {
  const sectionRef = useRef<HTMLElement>(null);
  const [revealedWordCount, setRevealedWordCount] = useState(0);
  const [revealedStepCount, setRevealedStepCount] = useState(0);
  const [isDescRevealed, setIsDescRevealed] = useState(false);
  const [isReducedMotion, setIsReducedMotion] = useState(false);

  useEffect(() => {
    // Respect prefers-reduced-motion
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) {
      setIsReducedMotion(true);
      setRevealedWordCount(HEADLINE_WORDS.length);
      setIsDescRevealed(true);
      setRevealedStepCount(PIPELINE_STEPS.length);
      return;
    }

    let started = false;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started) {
          started = true;
          observer.disconnect();

          // 1. Reveal headline words ONE BY ONE (NOT typewriter)
          HEADLINE_WORDS.forEach((_, idx) => {
            setTimeout(() => {
              setRevealedWordCount((prev) => Math.max(prev, idx + 1));
            }, idx * 160); // 160ms between words
          });

          // 2. Reveal description paragraph after headline finishes
          const descDelay = HEADLINE_WORDS.length * 160 + 200;
          setTimeout(() => {
            setIsDescRevealed(true);
          }, descDelay);

          // 3. Reveal workflow steps ONE BY ONE
          const workflowStartDelay = descDelay + 350;
          PIPELINE_STEPS.forEach((_, idx) => {
            setTimeout(() => {
              setRevealedStepCount((prev) => Math.max(prev, idx + 1));
            }, workflowStartDelay + idx * 220); // 220ms between steps
          });
        }
      },
      { threshold: 0.15 }
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <section
      ref={sectionRef}
      id="arm-intro"
      className="relative w-full py-24 px-6 max-w-6xl mx-auto border-t border-zinc-200 dark:border-zinc-900 transition-colors duration-300"
    >
      {/* Header Container */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        {/* Category tag */}
        <p className="text-xs uppercase tracking-[0.25em] text-blue-600 dark:text-blue-400 font-mono font-medium mb-3">
          Introduction
        </p>

        {/* Main Headline: Words revealed ONE BY ONE (Masked upward slide, NOT typewriter) */}
        <h2 className="text-3xl sm:text-5xl font-light text-zinc-900 dark:text-white tracking-tight leading-tight my-2 flex flex-wrap justify-center items-center">
          {HEADLINE_WORDS.map((word, idx) => {
            const isRevealed = isReducedMotion || idx < revealedWordCount;
            return (
              <span
                key={idx}
                className="overflow-hidden inline-block py-1 mr-2 sm:mr-3"
              >
                <span
                  className={cn(
                    "inline-block transition-all duration-700 ease-out transform",
                    isRevealed
                      ? "translate-y-0 opacity-100 filter-none"
                      : "translate-y-full opacity-0 blur-[3px]"
                  )}
                >
                  {word}
                </span>
              </span>
            );
          })}
        </h2>

        {/* Supporting description revealed smoothly after headline */}
        <div className="overflow-hidden mt-4">
          <p
            className={cn(
              "text-base sm:text-lg text-zinc-600 dark:text-zinc-400 font-normal leading-relaxed transition-all duration-800 ease-out transform",
              isReducedMotion || isDescRevealed
                ? "translate-y-0 opacity-100"
                : "translate-y-8 opacity-0"
            )}
          >
            ARM helps students create academic project reports, seminar reports, weekly reports, documentation, and other academic documents using their college&apos;s required format.
          </p>
        </div>
      </div>

      {/* Visual Workflow Steps: Revealed ONE BY ONE */}
      <div className="mb-16">
        <p
          className={cn(
            "text-xs font-mono uppercase tracking-widest text-zinc-500 dark:text-zinc-500 text-center mb-8 transition-opacity duration-700",
            isReducedMotion || revealedStepCount > 0 ? "opacity-100" : "opacity-0"
          )}
        >
          The Authentic Generation Pipeline
        </p>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 relative">
          {PIPELINE_STEPS.map((step, idx) => {
            const Icon = step.icon;
            const isStepRevealed = isReducedMotion || idx < revealedStepCount;

            return (
              <div
                key={step.title}
                className={cn(
                  "group relative flex flex-col items-center text-center p-6 rounded-2xl border transition-all duration-600 ease-out transform",
                  "bg-zinc-50 dark:bg-zinc-950/70 border-zinc-200 dark:border-zinc-800 hover:border-zinc-400 dark:hover:border-zinc-700 shadow-sm",
                  isStepRevealed
                    ? "translate-y-0 opacity-100 scale-100"
                    : "translate-y-8 opacity-0 scale-95"
                )}
              >
                <div className="w-12 h-12 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center text-zinc-700 dark:text-zinc-300 mb-4 group-hover:text-blue-600 dark:group-hover:text-white transition-colors shadow-sm">
                  <Icon className="w-5 h-5" />
                </div>
                <div className="text-xs font-mono text-zinc-500 dark:text-zinc-500 mb-1">
                  Step 0{idx + 1}
                </div>
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-white mb-2">
                  {step.title}
                </h3>
                <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-normal">
                  {step.desc}
                </p>
                {idx < PIPELINE_STEPS.length - 1 && (
                  <div className="hidden md:flex absolute -right-3 top-1/2 -translate-y-1/2 z-10 text-zinc-400 dark:text-zinc-600 pointer-events-none">
                    <ArrowRight className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
