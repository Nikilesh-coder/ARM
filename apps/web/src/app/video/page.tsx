import React from "react";
import Link from "next/link";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { ArmProductVideo } from "@/components/arm/arm-product-video";
import { SCENES } from "@/components/arm/video-scenes";
import { ArrowRight, Sparkles, ShieldCheck, CheckCircle2, Download, Film } from "lucide-react";

export const metadata = {
  title: "ARM AI — Product Intro Video & Motion Graphics",
  description:
    "Cinematic motion-graphics tour of ARM: College Template → Student Project → ARM AI → Intelligent Replacement → Final Report.",
};

export default function VideoPage() {
  return (
    <div className="min-h-screen bg-black text-white flex flex-col transition-colors duration-300">
      {/* Top Navigation */}
      <PublicNav />

      {/* Hero Header */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12 flex flex-col items-center">
        <div className="text-center max-w-3xl mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-xs font-mono text-emerald-400 mb-3 shadow-xs">
            <Sparkles className="w-3.5 h-3.5" />
            Official Product Introduction • 42s Motion Graphics
          </div>
          <h1 className="text-3xl sm:text-5xl font-light text-white tracking-tight">
            Academic Report Made Intelligent
          </h1>
          <p className="text-sm sm:text-base text-zinc-400 mt-2 font-light">
            Watch how ARM understands your college template and intelligently replaces the
            content while preserving 100% of the institutional design.
          </p>
        </div>

        {/* Action Bar: Download Video & File Specs */}
        <div className="w-full mb-4 flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-zinc-900/80 border border-zinc-800 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Film className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-white">ARM_Motion_Graphics.mp4</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Ready to Download
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                MP4 • H.264 / AAC • 720p HD (1280×720) • 24 FPS • 1.65 MB • Opens in VLC / WMP / QuickTime
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <a
              href="/ARM_Motion_Graphics.mp4"
              download="ARM_Motion_Graphics.mp4"
              className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-all flex items-center gap-2 shadow-lg shadow-emerald-500/20 hover:scale-105 active:scale-95 cursor-pointer"
            >
              <Download className="w-4 h-4 stroke-[2.5]" />
              Download Video
            </a>
          </div>
        </div>

        {/* Cinematic Video Player Container */}
        <div className="w-full mb-12 shadow-2xl">
          <ArmProductVideo />
        </div>

        {/* Scene Chapter Grid */}
        <div className="w-full border-t border-zinc-900 pt-10">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">Video Chapters & Architecture</h2>
              <p className="text-xs text-zinc-400">
                13 curated scenes detailing the deterministic report assembly pipeline.
              </p>
            </div>
            <Link
              href="/app"
              className="px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold hover:bg-emerald-500/20 transition-colors flex items-center gap-1.5"
            >
              Open ARM Workspace <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {SCENES.map((scene) => (
              <div
                key={scene.id}
                className="p-3.5 rounded-xl bg-zinc-950 border border-zinc-850 hover:border-zinc-700 transition-colors"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-mono text-emerald-400 font-semibold">
                    SCENE {scene.id.toString().padStart(2, "0")}
                  </span>
                  <span className="text-[10px] font-mono text-zinc-500">
                    {scene.startTime.toFixed(1)}s
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-white">{scene.title}</h4>
                <p className="text-[11px] text-zinc-400 mt-0.5 leading-snug">{scene.subtitle}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Key Product Value Proposition */}
        <div className="w-full mt-12 p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center shrink-0">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">
                Zero Redesign • 100% College Template Preservation
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Margins, fonts, logos, borders, Roman page numbers, and spacing remain completely
                untouched.
              </p>
            </div>
          </div>
          <Link
            href="/app"
            className="px-6 py-2.5 rounded-xl bg-white text-black font-semibold text-xs hover:bg-zinc-200 transition-all shrink-0 flex items-center gap-2"
          >
            Launch ARM Workspace <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </main>

      {/* Footer */}
      <PublicFooter />
    </div>
  );
}
