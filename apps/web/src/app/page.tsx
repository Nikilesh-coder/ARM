import React from "react";
import Link from "next/link";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { ArmWelcome } from "@/components/arm/arm-welcome";
import { ArmIntro } from "@/components/arm/arm-intro";
import { ThemeSelector } from "@/components/arm/theme-selector";
import { GetStartedSection } from "@/components/arm/get-started-section";
import { ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-black text-white flex flex-col transition-colors duration-300">
      {/* SECTIONS 1 & 2: Cinematic Intro Zone (Always Dark) */}
      <div className="dark bg-black text-zinc-100 w-full flex flex-col">
        {/* 1. Full-Screen Cinematic Welcome with Typewriter Effect */}
        <ArmWelcome />

        {/* Sticky Header as user enters platform content */}
        <PublicNav />

        {/* 2. ARM Introduction & Visual Workflow (Revealed ONE BY ONE, NOT typewriter) */}
        <ArmIntro />
      </div>

      {/* SECTIONS 3 to 5: Theme-Responsive Zone (Light Theme only active up to #5) */}
      <div className="w-full bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 transition-colors duration-300">
        {/* 3. Theme Selection: Dark, Light, System (Changes background colour instantly for #3 to #5) */}
        <ThemeSelector />

        {/* 4. Primary Call to Action: Get Started Right After Theme Selection */}
        <GetStartedSection />


      </div>

      {/* SECTIONS 6 & 7: Knowledge Base & Footer Zone (Always Dark) */}
      <div className="dark bg-black text-zinc-100 w-full flex flex-col">
        {/* 6. Academic FAQ preview */}
        <section className="py-20 px-6 max-w-4xl mx-auto border-t border-zinc-900 w-full transition-colors duration-300">
          <div className="text-center mb-12">
            <span className="text-xs uppercase tracking-widest text-zinc-500 font-mono">
              Questions & Answers
            </span>
            <h2 className="text-2xl sm:text-3xl font-light text-white tracking-tight mt-2">
              Frequently Asked Questions
            </h2>
          </div>

          <div className="space-y-4">
            <div className="p-5 rounded-xl border border-zinc-850 bg-zinc-950/50 shadow-xs transition-colors duration-300">
              <h4 className="text-sm font-semibold text-white mb-1.5">
                Can ARM follow my college&apos;s exact Word template?
              </h4>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Yes. You upload your institution&apos;s official .docx sample once. ARM analyzes the document structure and extracts paragraph styles, margins, and headings to format future generated drafts.
              </p>
            </div>

            <div className="p-5 rounded-xl border border-zinc-850 bg-zinc-950/50 shadow-xs transition-colors duration-300">
              <h4 className="text-sm font-semibold text-white mb-1.5">
                Does ARM verify generated content before export?
              </h4>
              <p className="text-xs text-zinc-400 leading-relaxed">
                ARM cross-checks section word counts, heading hierarchy, and citation formats before assembling final binaries. You have complete inspection and editing control before downloading.
              </p>
            </div>

            <div className="p-5 rounded-xl border border-zinc-850 bg-zinc-950/50 shadow-xs transition-colors duration-300">
              <h4 className="text-sm font-semibold text-white mb-1.5">
                What files can I attach in the AI Workspace?
              </h4>
              <p className="text-xs text-zinc-400 leading-relaxed">
                The workspace supports Word templates (.docx), research papers (.pdf), architecture diagrams (.png, .jpg), demonstration videos (.mp4), datasets (.csv), and source code (.py, .ts, .zip).
              </p>
            </div>
          </div>

          <div className="mt-8 text-center">
            <Link href="/faq" className="text-xs text-blue-400 hover:underline font-medium inline-flex items-center gap-1">
              View all academic FAQ answers <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </section>

        {/* 7. Footer */}
        <PublicFooter />
      </div>
    </div>
  );
}
