"use client";

import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight, BookOpen } from "lucide-react";

export function GetStartedSection() {
  return (
    <section className="relative w-full py-20 px-6 max-w-4xl mx-auto text-center border-t border-zinc-200 dark:border-zinc-900 transition-colors duration-300">
      <div className="p-10 sm:p-14 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-gradient-to-b from-zinc-50 to-white dark:from-zinc-900/60 dark:to-zinc-950/80 shadow-xl relative overflow-hidden transition-colors duration-300">
        <div className="relative z-10">
          <h2 className="text-3xl sm:text-4xl font-light text-zinc-900 dark:text-white tracking-tight mb-4">
            Ready to create your report?
          </h2>
          <p className="text-zinc-600 dark:text-zinc-400 text-sm sm:text-base max-w-lg mx-auto mb-8 font-normal leading-relaxed">
            Attach your project evidence, specify your university formatting rules, and let ARM assemble your academic documentation.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/signup">
              <Button variant="primary" size="lg" className="w-full sm:w-auto font-medium">
                Get Started
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
            <Link href="/how-it-works">
              <Button variant="outline" size="lg" className="w-full sm:w-auto">
                <BookOpen className="w-4 h-4 mr-1 text-zinc-500 dark:text-zinc-400" />
                Learn More
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
