import React from "react";
import Link from "next/link";

export function PublicFooter() {
  return (
    <footer className="border-t border-zinc-200 dark:border-zinc-900 bg-zinc-50 dark:bg-black text-zinc-600 dark:text-zinc-400 text-xs transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
          {/* Brand info */}
          <div className="col-span-2 space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 rounded-lg bg-zinc-900 border border-zinc-750 flex items-center justify-center text-white font-mono font-bold text-xs">
                ARM
              </div>
              <span className="font-semibold text-zinc-900 dark:text-white tracking-tight">ARM</span>
            </div>
            <p className="text-zinc-600 dark:text-zinc-500 max-w-sm leading-relaxed text-xs">
              AI Academic Report Assistant. Designed to follow your college format. Generate university-compliant project reports, seminar documentation, and weekly diaries from your genuine evidence.
            </p>
            <div className="pt-2 text-[11px] text-zinc-500 dark:text-zinc-600 font-mono">
              Deterministic OpenXML Document Engine
            </div>
          </div>

          {/* Product */}
          <div>
            <h4 className="font-semibold text-zinc-900 dark:text-white mb-3 tracking-wide">Platform</h4>
            <ul className="space-y-2">
              <li><Link href="/features" className="hover:text-zinc-950 dark:hover:text-white transition-colors">Features</Link></li>
              <li><Link href="/how-it-works" className="hover:text-zinc-950 dark:hover:text-white transition-colors">How It Works</Link></li>
              <li><Link href="/pricing" className="hover:text-zinc-950 dark:hover:text-white transition-colors">Pricing</Link></li>
              <li><Link href="/faq" className="hover:text-zinc-950 dark:hover:text-white transition-colors">FAQ</Link></li>
            </ul>
          </div>

          {/* App Workspace */}
          <div>
            <h4 className="font-semibold text-zinc-900 dark:text-white mb-3 tracking-wide">Workspace</h4>
            <ul className="space-y-2">
              <li><Link href="/app" className="hover:text-zinc-950 dark:hover:text-white transition-colors">AI Workspace</Link></li>
              <li><Link href="/app/projects" className="hover:text-zinc-950 dark:hover:text-white transition-colors">Projects</Link></li>
              <li><Link href="/app/templates" className="hover:text-zinc-950 dark:hover:text-white transition-colors">Templates</Link></li>
              <li><Link href="/app/evidence" className="hover:text-zinc-950 dark:hover:text-white transition-colors">Evidence Locker</Link></li>
            </ul>
          </div>

          {/* Academic Integrity */}
          <div>
            <h4 className="font-semibold text-zinc-900 dark:text-white mb-3 tracking-wide">Compliance</h4>
            <ul className="space-y-2">
              <li><Link href="/faq" className="hover:text-zinc-950 dark:hover:text-white transition-colors">Format Matching</Link></li>
              <li><Link href="/faq" className="hover:text-zinc-950 dark:hover:text-white transition-colors">Plagiarism Safety</Link></li>
              <li><Link href="/faq" className="hover:text-zinc-950 dark:hover:text-white transition-colors">IEEE / APA Citations</Link></li>
              <li><Link href="/login" className="hover:text-zinc-950 dark:hover:text-white transition-colors">Student Login</Link></li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-zinc-200 dark:border-zinc-900 flex flex-col sm:flex-row justify-between items-center gap-4 text-[11px] text-zinc-500 dark:text-zinc-600">
          <p>© {new Date().getFullYear()} ARM. Academic Report Assistant. All rights reserved.</p>
          <div className="flex items-center space-x-6">
            <span className="hover:text-zinc-700 dark:hover:text-zinc-400 transition-colors">Institutional Privacy</span>
            <span className="hover:text-zinc-700 dark:hover:text-zinc-400 transition-colors">Academic Terms</span>
            <span className="hover:text-zinc-700 dark:hover:text-zinc-400 transition-colors">Security</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
