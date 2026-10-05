"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/features", label: "Features" },
  { href: "/how-it-works", label: "How It Works" },
  { href: "/pricing", label: "Pricing" },
  { href: "/faq", label: "FAQ" },
];

export function PublicNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-zinc-200 dark:border-zinc-850 bg-white/80 dark:bg-black/80 backdrop-blur-md transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-750 flex items-center justify-center text-white font-mono font-bold text-xs tracking-wider shadow-xs">
            ARM
          </div>
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-base text-zinc-900 dark:text-white tracking-tight">
              ARM
            </span>
            <span className="text-[10px] uppercase font-mono tracking-wider px-2 py-0.5 bg-zinc-100 dark:bg-zinc-900 text-zinc-600 dark:text-zinc-400 rounded-full border border-zinc-200 dark:border-zinc-800">
              Academic
            </span>
          </div>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center space-x-8 text-xs font-medium text-zinc-600 dark:text-zinc-400">
          {NAV_LINKS.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={
                  active
                    ? "text-zinc-900 dark:text-white font-semibold"
                    : "hover:text-zinc-900 dark:hover:text-zinc-200 transition-colors"
                }
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Auth CTA */}
        <div className="hidden sm:flex items-center space-x-3">
          <Link
            href="/login"
            className="text-xs font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white px-3 py-1.5 transition-colors"
          >
            Log in
          </Link>
          <Link href="/signup">
            <Button variant="primary" size="sm" className="text-xs">
              Get Started <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
            </Button>
          </Link>
        </div>

        {/* Mobile Hamburger */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden p-2 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="md:hidden border-b border-zinc-200 dark:border-zinc-850 bg-white dark:bg-black px-4 pt-3 pb-6 space-y-3">
          <div className="flex flex-col space-y-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className={`px-3 py-2 rounded-lg text-xs font-medium ${
                  pathname === link.href
                    ? "bg-zinc-100 dark:bg-zinc-900 text-zinc-900 dark:text-white font-semibold"
                    : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-950 hover:text-zinc-900 dark:hover:text-zinc-200"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>
          <div className="pt-3 border-t border-zinc-200 dark:border-zinc-850 flex flex-col gap-2">
            <Link href="/login" onClick={() => setMobileOpen(false)}>
              <Button variant="outline" className="w-full text-xs">
                Log in
              </Button>
            </Link>
            <Link href="/signup" onClick={() => setMobileOpen(false)}>
              <Button variant="primary" className="w-full text-xs">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
