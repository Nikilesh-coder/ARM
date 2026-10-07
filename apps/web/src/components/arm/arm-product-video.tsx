"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import Link from "next/link";
import {
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  Maximize2,
  Minimize2,
  Sparkles,
  FileCode2,
  Cpu,
  CheckCircle2,
  ShieldCheck,
  FileText,
  FolderGit2,
  ArrowRight,
  Database,
  Layers,
  Settings,
  Check,
  Download,
  MousePointer2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";
import { SCENES, TOTAL_VIDEO_DURATION, SceneConfig } from "./video-scenes";

const TOTAL_DURATION = TOTAL_VIDEO_DURATION;

// =============================================================================
// SYNTHESIZED WEB AUDIO API SOUND ENGINE
// =============================================================================
class WebAudioSynthesizer {
  private ctx: AudioContext | null = null;
  private ambientOsc1: OscillatorNode | null = null;
  private ambientOsc2: OscillatorNode | null = null;
  private ambientGain: GainNode | null = null;
  private isMuted: boolean = false;

  private ensureContext(): AudioContext | null {
    if (typeof window === "undefined") return null;
    if (!this.ctx) {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioContextClass) {
        this.ctx = new AudioContextClass();
      }
    }
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
    return this.ctx;
  }

  public setMuted(muted: boolean) {
    this.isMuted = muted;
    if (this.ambientGain) {
      this.ambientGain.gain.value = muted ? 0 : 0.035;
    }
  }

  public startAmbient() {
    if (this.isMuted) return;
    const ctx = this.ensureContext();
    if (!ctx || this.ambientOsc1) return;

    try {
      this.ambientOsc1 = ctx.createOscillator();
      this.ambientOsc2 = ctx.createOscillator();
      this.ambientGain = ctx.createGain();
      const filter = ctx.createBiquadFilter();

      this.ambientOsc1.type = "sine";
      this.ambientOsc1.frequency.setValueAtTime(65, ctx.currentTime);

      this.ambientOsc2.type = "sine";
      this.ambientOsc2.frequency.setValueAtTime(130.8, ctx.currentTime);

      filter.type = "lowpass";
      filter.frequency.setValueAtTime(220, ctx.currentTime);

      this.ambientGain.gain.setValueAtTime(0.001, ctx.currentTime);
      this.ambientGain.gain.exponentialRampToValueAtTime(0.035, ctx.currentTime + 1.5);

      this.ambientOsc1.connect(filter);
      this.ambientOsc2.connect(filter);
      filter.connect(this.ambientGain);
      this.ambientGain.connect(ctx.destination);

      this.ambientOsc1.start();
      this.ambientOsc2.start();
    } catch {}
  }

  public stopAmbient() {
    if (this.ambientOsc1) {
      try {
        this.ambientOsc1.stop();
        this.ambientOsc2?.stop();
        this.ambientOsc1.disconnect();
        this.ambientOsc2?.disconnect();
      } catch {}
      this.ambientOsc1 = null;
      this.ambientOsc2 = null;
      this.ambientGain = null;
    }
  }

  public playWhoosh() {
    if (this.isMuted) return;
    const ctx = this.ensureContext();
    if (!ctx) return;

    try {
      const bufferSize = ctx.sampleRate * 0.35;
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.3));
      }

      const noise = ctx.createBufferSource();
      noise.buffer = buffer;

      const filter = ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.setValueAtTime(650, ctx.currentTime);
      filter.frequency.exponentialRampToValueAtTime(120, ctx.currentTime + 0.32);
      filter.Q.setValueAtTime(2.5, ctx.currentTime);

      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.32);

      noise.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);
      noise.start();
    } catch {}
  }

  public playClick() {
    if (this.isMuted) return;
    const ctx = this.ensureContext();
    if (!ctx) return;

    try {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.setValueAtTime(1400, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(280, ctx.currentTime + 0.035);

      gain.gain.setValueAtTime(0.045, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.035);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.04);
    } catch {}
  }

  public playPulse() {
    if (this.isMuted) return;
    const ctx = this.ensureContext();
    if (!ctx) return;

    try {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(392, ctx.currentTime); // G4
      osc.frequency.exponentialRampToValueAtTime(784, ctx.currentTime + 0.14);

      gain.gain.setValueAtTime(0.04, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.16);
    } catch {}
  }

  public playSuccess() {
    if (this.isMuted) return;
    const ctx = this.ensureContext();
    if (!ctx) return;

    try {
      const notes = [523.25, 659.25, 783.99, 1046.5]; // C5, E5, G5, C6
      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        const startTime = ctx.currentTime + idx * 0.08;
        osc.frequency.setValueAtTime(freq, startTime);

        gain.gain.setValueAtTime(0.04, startTime);
        gain.gain.exponentialRampToValueAtTime(0.0005, startTime + 0.42);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(startTime);
        osc.stop(startTime + 0.45);
      });
    } catch {}
  }
}

const soundSynth = new WebAudioSynthesizer();

// =============================================================================
// MAIN COMPONENT: ArmProductVideo
// =============================================================================
export function ArmProductVideo() {
  const containerRef = useRef<HTMLDivElement>(null);

  // Playback States
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [playbackRate, setPlaybackRate] = useState<number>(1);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showControls, setShowControls] = useState<boolean>(true);
  const [activeUser, setActiveUser] = useState<string>("Engineering Scholar");

  const lastScenePlayedRef = useRef<number>(-1);
  const controlsTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 1. Dynamic User Identity Fetch (Supabase Auth + Local Storage)
  useEffect(() => {
    async function resolveIdentity() {
      try {
        if (typeof window !== "undefined") {
          const localStored = localStorage.getItem("arm_user_name");
          if (localStored && localStored.trim().length > 0) {
            setActiveUser(localStored.trim());
            return;
          }
        }
        const { data } = await supabase.auth.getUser();
        if (data?.user) {
          const meta = data.user.user_metadata;
          const candidate =
            meta?.full_name || meta?.name || meta?.user_name || data.user.email?.split("@")[0];
          if (candidate) {
            setActiveUser(candidate);
          }
        }
      } catch {}
    }
    resolveIdentity();
  }, []);

  // 2. Playback Animation Engine Loop (60fps)
  useEffect(() => {
    let animId: number;
    let lastTs = performance.now();

    const loop = (now: number) => {
      const dt = (now - lastTs) / 1000;
      lastTs = now;

      if (isPlaying) {
        setCurrentTime((prev) => {
          const next = prev + dt * playbackRate;
          if (next >= TOTAL_DURATION) {
            setIsPlaying(false);
            return TOTAL_DURATION;
          }
          return next;
        });
      }
      animId = requestAnimationFrame(loop);
    };

    animId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, playbackRate]);

  // Active scene resolution
  const activeSceneIndex = useMemo(() => {
    for (let i = SCENES.length - 1; i >= 0; i--) {
      if (currentTime >= SCENES[i].startTime) {
        return i;
      }
    }
    return 0;
  }, [currentTime]);

  const currentScene = SCENES[activeSceneIndex];
  const sceneProgress = useMemo(() => {
    const elapsed = currentTime - currentScene.startTime;
    return Math.min(1, Math.max(0, elapsed / currentScene.duration));
  }, [currentTime, currentScene]);

  // Audio cues on scene transitions
  useEffect(() => {
    if (activeSceneIndex !== lastScenePlayedRef.current) {
      lastScenePlayedRef.current = activeSceneIndex;

      if (isPlaying && !isMuted) {
        soundSynth.startAmbient();

        if (activeSceneIndex === 0) {
          soundSynth.playPulse();
        } else if (activeSceneIndex === 4 || activeSceneIndex === 5) {
          soundSynth.playClick();
        } else if (activeSceneIndex === 8) {
          soundSynth.playPulse();
        } else if (activeSceneIndex === 9) {
          soundSynth.playWhoosh();
        } else if (activeSceneIndex === 11 || activeSceneIndex === 12) {
          soundSynth.playSuccess();
        } else {
          soundSynth.playWhoosh();
        }
      }
    }
  }, [activeSceneIndex, isPlaying, isMuted]);

  const toggleMute = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    soundSynth.setMuted(nextMuted);
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        e.preventDefault();
        setIsPlaying((p) => !p);
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        setCurrentTime((t) => Math.min(TOTAL_DURATION, t + 4));
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        setCurrentTime((t) => Math.max(0, t - 4));
      } else if (e.code === "KeyM") {
        e.preventDefault();
        toggleMute();
      } else if (e.code === "KeyF") {
        e.preventDefault();
        handleToggleFullscreen();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isMuted]);

  const handleMouseMove = () => {
    setShowControls(true);
    if (controlsTimeoutRef.current) clearTimeout(controlsTimeoutRef.current);
    controlsTimeoutRef.current = setTimeout(() => {
      if (isPlaying) setShowControls(false);
    }, 2800);
  };

  const handleToggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  const jumpToScene = (index: number) => {
    const target = SCENES[index];
    if (target) {
      setCurrentTime(target.startTime + 0.05);
      soundSynth.playClick();
    }
  };

  const restartVideo = () => {
    setCurrentTime(0);
    setIsPlaying(true);
    lastScenePlayedRef.current = -1;
    soundSynth.playWhoosh();
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Parallax floating offsets (derived smoothly from currentTime)
  const floatY = Math.sin(currentTime * 1.8) * 6;
  const floatX = Math.cos(currentTime * 1.2) * 4;

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      className={cn(
        "relative w-full aspect-[16/9] max-h-[85vh] bg-[#070709] text-white rounded-2xl overflow-hidden shadow-2xl border border-zinc-850 select-none flex flex-col justify-between transition-all",
        isFullscreen && "max-h-none h-screen rounded-none border-none"
      )}
    >
      {/* =====================================================================
          CINEMATIC STAGE: 3D VIEWPORT WITH PARALLAX & CAMERA MOVEMENT
          ===================================================================== */}
      <div
        className="relative flex-1 w-full h-full overflow-hidden flex items-center justify-center bg-[#070709]"
        style={{ perspective: "1300px" }}
      >
        {/* Dynamic Parallax Background Mesh & Breathing Lighting */}
        <div
          className="absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,rgba(24,32,28,0.7)_0%,rgba(7,7,9,1)_80%)] pointer-events-none transition-transform duration-1000 ease-out"
          style={{
            transform: `scale(${1 + sceneProgress * 0.04}) translate3d(${floatX * 0.3}px, ${floatY * 0.3}px, 0)`,
          }}
        />

        {/* Subtle Ambient Particle Field */}
        <div className="absolute inset-0 opacity-20 pointer-events-none overflow-hidden">
          <div
            className="absolute w-2 h-2 rounded-full bg-emerald-400 blur-[1px]"
            style={{
              top: `${20 + Math.sin(currentTime * 0.8) * 15}%`,
              left: `${15 + Math.cos(currentTime * 0.6) * 10}%`,
            }}
          />
          <div
            className="absolute w-3 h-3 rounded-full bg-cyan-400 blur-[2px]"
            style={{
              top: `${65 + Math.cos(currentTime * 0.7) * 20}%`,
              right: `${20 + Math.sin(currentTime * 0.5) * 12}%`,
            }}
          />
          <div
            className="absolute w-2 h-2 rounded-full bg-emerald-300 blur-[1px]"
            style={{
              bottom: `${25 + Math.sin(currentTime * 1.1) * 10}%`,
              left: `${45 + Math.cos(currentTime * 0.9) * 15}%`,
            }}
          />
        </div>

        {/* -------------------------------------------------------------------
            SCENE 1: ARM INTRO (Typewriter + Glowing Aura)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 0 && (
          <div
            className="relative z-10 text-center px-6 max-w-3xl flex flex-col items-center transition-all duration-700 ease-out"
            style={{
              transform: `scale(${1 + sceneProgress * 0.06}) translate3d(0, ${-sceneProgress * 8}px, 0)`,
              opacity: sceneProgress > 0.9 ? 1 - (sceneProgress - 0.9) * 10 : 1,
            }}
          >
            {/* Glowing Logo Badge */}
            <div className="w-14 h-14 mb-6 rounded-2xl bg-zinc-900 border border-emerald-500/30 flex items-center justify-center shadow-[0_0_30px_rgba(52,211,153,0.15)] animate-pulse">
              <span className="font-mono text-base font-bold text-white tracking-widest">ARM</span>
            </div>

            <h1 className="text-5xl sm:text-7xl font-extralight tracking-tight text-white mb-4">
              {sceneProgress > 0.45 ? (
                <>
                  Welcome to <span className="font-semibold text-emerald-300">ARM</span>
                </>
              ) : (
                "Hello"
              )}
              <span className="inline-block w-1 h-12 ml-2 bg-emerald-400 animate-ping align-middle" />
            </h1>

            <p
              className={cn(
                "text-xs sm:text-sm font-mono tracking-[0.3em] uppercase text-zinc-400 transition-all duration-700",
                sceneProgress > 0.55 ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              )}
            >
              Academic Report Maker • AI Engine
            </p>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 2: MEET ARM (Neural Mesh & Orbiting Nodes)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 1 && (
          <div
            className="relative z-10 text-center px-6 max-w-2xl flex flex-col items-center transition-all duration-700 ease-out"
            style={{
              transform: `scale(${1 + sceneProgress * 0.05}) translate3d(${floatX * 0.5}px, ${floatY * 0.5}px, 0)`,
            }}
          >
            {/* Sophisticated Neural Mesh Visualization */}
            <div className="relative w-36 h-36 mb-8 flex items-center justify-center">
              {/* Outer Pulsing Synapse Ring */}
              <div className="absolute inset-0 rounded-full border border-emerald-500/20 animate-ping" />
              {/* Middle 3D Tilt Ring */}
              <div
                className="absolute inset-2 rounded-full border border-cyan-500/30 border-dashed animate-spin"
                style={{ animationDuration: "14s" }}
              />
              {/* Core AI Orb */}
              <div className="relative w-24 h-24 rounded-full border border-emerald-500/50 bg-zinc-900/80 backdrop-blur-md flex items-center justify-center shadow-[0_0_35px_rgba(52,211,153,0.25)]">
                <Cpu className="w-10 h-10 text-emerald-400 animate-pulse" />
              </div>
              {/* Floating Synaptic Packets */}
              <div
                className="absolute w-3 h-3 rounded-full bg-emerald-400 shadow-lg shadow-emerald-500"
                style={{
                  top: `${15 + Math.sin(currentTime * 3) * 20}%`,
                  left: `${10 + Math.cos(currentTime * 3) * 15}%`,
                }}
              />
              <div
                className="absolute w-3 h-3 rounded-full bg-cyan-400 shadow-lg shadow-cyan-500"
                style={{
                  bottom: `${15 + Math.cos(currentTime * 2.5) * 20}%`,
                  right: `${10 + Math.sin(currentTime * 2.5) * 15}%`,
                }}
              />
            </div>

            <h2 className="text-4xl sm:text-6xl font-light text-white tracking-tight mb-3">
              Meet <span className="font-bold text-emerald-400">ARM</span>
            </h2>
            <p className="text-lg sm:text-xl text-zinc-300 font-light max-w-md">
              Your AI-powered academic report assistant.
            </p>
            <div className="mt-6 flex items-center gap-2 px-4 py-1.5 rounded-full bg-zinc-900/80 border border-zinc-750 text-xs font-mono text-zinc-300 shadow-md">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Context-Aware Formatting Model 2.0
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 3: PERSONALIZED EXPERIENCE (Dynamic Scholar Session)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 2 && (
          <div
            className="relative z-10 text-center px-6 max-w-3xl flex flex-col items-center transition-all duration-700 ease-out"
            style={{
              transform: `scale(${1 + sceneProgress * 0.05}) translate3d(0, ${-sceneProgress * 6}px, 0)`,
            }}
          >
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-zinc-900 border border-zinc-750 text-xs font-mono text-emerald-400 mb-6 shadow-lg">
              <Check className="w-3.5 h-3.5" />
              Authenticated Session Verified
            </div>

            <h2 className="text-4xl sm:text-6xl md:text-7xl font-extralight text-white tracking-tight mb-4">
              Hello, <span className="font-semibold text-emerald-300">{activeUser}</span>
            </h2>

            <p className="text-sm sm:text-base text-zinc-400 font-light max-w-lg animate-pulse">
              Preparing your college templates and project evidence...
            </p>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 4: DASHBOARD CINEMATIC PUSH (3D Floating Perspective)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 3 && (
          <div
            className="relative z-10 w-full max-w-5xl px-6 h-full flex flex-col justify-center transition-transform duration-1000 ease-out"
            style={{
              transform: `perspective(1200px) rotateX(${4 - sceneProgress * 2}deg) rotateY(${-2 + sceneProgress * 2}deg) scale(${
                0.94 + sceneProgress * 0.06
              }) translate3d(${floatX * 0.4}px, ${floatY * 0.4}px, 0)`,
            }}
          >
            {/* Top Workspace Chrome */}
            <div className="w-full bg-zinc-900/90 border border-zinc-750 rounded-t-xl px-4 py-2.5 flex items-center justify-between text-xs text-zinc-400 shadow-xl backdrop-blur-md">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <div className="w-3 h-3 rounded-full bg-green-500/80" />
                <span className="ml-3 font-mono text-zinc-300">arm.app/workspace</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-emerald-400 text-[11px] font-mono">● System Online</span>
                <span className="text-zinc-600">|</span>
                <span className="text-zinc-200 font-medium">{activeUser}</span>
              </div>
            </div>

            {/* Dashboard Workspace */}
            <div className="w-full bg-zinc-950/90 border-x border-b border-zinc-750 rounded-b-xl p-4 sm:p-6 grid grid-cols-12 gap-4 shadow-2xl backdrop-blur-xl">
              {/* Left Sidebar with Sequential Focused Glows */}
              <div className="col-span-4 sm:col-span-3 bg-zinc-900/80 border border-zinc-800 rounded-lg p-3 space-y-2 text-xs">
                <div
                  className={cn(
                    "p-2 rounded flex items-center gap-2 transition-all duration-300",
                    sceneProgress < 0.25
                      ? "bg-emerald-500/25 text-emerald-300 ring-2 ring-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.3)]"
                      : "text-zinc-400"
                  )}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span className="font-semibold">New Report</span>
                </div>
                <div
                  className={cn(
                    "p-2 rounded flex items-center gap-2 transition-all duration-300",
                    sceneProgress >= 0.25 && sceneProgress < 0.5
                      ? "bg-emerald-500/25 text-emerald-300 ring-2 ring-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.3)]"
                      : "text-zinc-400"
                  )}
                >
                  <FileCode2 className="w-3.5 h-3.5" />
                  <span>Templates</span>
                </div>
                <div
                  className={cn(
                    "p-2 rounded flex items-center gap-2 transition-all duration-300",
                    sceneProgress >= 0.5 && sceneProgress < 0.75
                      ? "bg-emerald-500/25 text-emerald-300 ring-2 ring-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.3)]"
                      : "text-zinc-400"
                  )}
                >
                  <FolderGit2 className="w-3.5 h-3.5" />
                  <span>My Projects</span>
                </div>
                <div
                  className={cn(
                    "p-2 rounded flex items-center gap-2 transition-all duration-300",
                    sceneProgress >= 0.75
                      ? "bg-emerald-500/25 text-emerald-300 ring-2 ring-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.3)]"
                      : "text-zinc-400"
                  )}
                >
                  <Settings className="w-3.5 h-3.5" />
                  <span>Settings</span>
                </div>
              </div>

              {/* Main Workspace Panels with Independent Float */}
              <div
                className="col-span-8 sm:col-span-9 bg-zinc-900/50 border border-zinc-800 rounded-lg p-5 flex flex-col justify-between"
                style={{ transform: `translate3d(0, ${-floatY * 0.4}px, 0)` }}
              >
                <div>
                  <h3 className="text-base font-semibold text-white">Engineering Project Hub</h3>
                  <p className="text-xs text-zinc-400 mt-1">
                    Guided synthesis for major capstone & IEEE conference papers.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3 mt-4">
                  <div className="p-3.5 rounded-lg bg-zinc-950/80 border border-emerald-500/30 shadow-md">
                    <span className="text-[10px] text-zinc-500 uppercase font-mono">Active Model</span>
                    <p className="text-xs font-semibold text-emerald-400 mt-0.5">ARM Academic 2.0</p>
                  </div>
                  <div className="p-3.5 rounded-lg bg-zinc-950/80 border border-zinc-800 shadow-md">
                    <span className="text-[10px] text-zinc-500 uppercase font-mono">Template Lock</span>
                    <p className="text-xs font-semibold text-zinc-200 mt-0.5">Zero Drift Enforced</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 5: CREATE PROJECT (Natural Typing & Pointer Glide)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 4 && (
          <div
            className="relative z-10 w-full max-w-xl px-6 transition-transform duration-700 ease-out"
            style={{
              transform: `scale(${0.96 + sceneProgress * 0.04}) translate3d(0, ${-sceneProgress * 5}px, 0)`,
            }}
          >
            <div className="bg-zinc-900/95 border border-zinc-750 rounded-2xl p-6 shadow-2xl backdrop-blur-xl relative">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-800 mb-4">
                <div className="flex items-center gap-2">
                  <FolderGit2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm font-semibold text-white">Create New Academic Project</span>
                </div>
                <span className="text-[10px] font-mono text-zinc-400">Step 1 of 3</span>
              </div>

              {/* Title Field with Natural Typing */}
              <div className="space-y-1.5 mb-4">
                <label className="text-xs font-medium text-zinc-300">Project / Report Title</label>
                <div className="w-full bg-zinc-950 border border-emerald-500/60 rounded-xl px-3.5 py-2.5 text-xs font-mono text-white flex items-center shadow-inner">
                  <span>
                    {"AI Based Irrigation System".slice(0, Math.floor(sceneProgress * 30))}
                  </span>
                  <span className="w-1.5 h-3.5 bg-emerald-400 ml-1 animate-pulse" />
                </div>
              </div>

              {/* Description Field */}
              <div className="space-y-1.5 mb-4">
                <label className="text-xs font-medium text-zinc-300">Description & Objectives</label>
                <div className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-xs text-zinc-300 h-16 leading-relaxed">
                  {sceneProgress > 0.35 ? (
                    "Smart IoT soil telemetry, predictive water dispatch, and automated valve regulation."
                  ) : (
                    <span className="text-zinc-600">Enter project scope...</span>
                  )}
                </div>
              </div>

              {/* Pill Selection with Floating Pointer Click */}
              <div className="flex items-center gap-2 pt-2 relative">
                <div className="px-3.5 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/50 text-[11px] font-mono text-emerald-300 flex items-center gap-1.5 shadow-md">
                  <Check className="w-3 h-3" />
                  IEEE Major Capstone Report
                </div>
                <div className="px-3 py-1.5 rounded-lg bg-zinc-850 border border-zinc-800 text-[11px] font-mono text-zinc-500">
                  Weekly Synopsis
                </div>

                {/* Animated Mouse Pointer */}
                <div
                  className="absolute pointer-events-none transition-all duration-500"
                  style={{
                    left: `${20 + Math.min(100, sceneProgress * 120)}px`,
                    top: `${sceneProgress > 0.6 ? 10 : 30}px`,
                  }}
                >
                  <MousePointer2 className="w-4 h-4 text-white fill-white drop-shadow-md" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 6: UPLOAD COLLEGE TEMPLATE (Decelerating Floating Card)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 5 && (
          <div
            className="relative z-10 w-full max-w-xl px-6 flex flex-col items-center transition-all duration-700 ease-out"
            style={{
              transform: `scale(${0.96 + sceneProgress * 0.04})`,
            }}
          >
            <h3 className="text-2xl sm:text-3xl font-light text-white mb-2 text-center">
              Upload your college template
            </h3>
            <p className="text-xs text-zinc-400 mb-6 text-center">
              Any institutional format: IEEE, Anna Univ, VTU, Mumbai Univ, or Autonomous.
            </p>

            <div className="w-full border-2 border-dashed border-zinc-700 bg-zinc-900/50 rounded-2xl p-8 flex flex-col items-center justify-center relative overflow-hidden backdrop-blur-md">
              {sceneProgress < 0.5 ? (
                // Floating Incoming DOCX Card
                <div
                  className="flex flex-col items-center transition-transform duration-700"
                  style={{
                    transform: `translate3d(0, ${Math.sin(sceneProgress * 4) * 10}px, 0) rotateZ(${
                      -2 + sceneProgress * 4
                    }deg)`,
                  }}
                >
                  <div className="w-16 h-16 rounded-2xl bg-blue-500/15 border border-blue-500/40 flex items-center justify-center mb-3 shadow-[0_0_20px_rgba(59,130,246,0.2)]">
                    <FileCode2 className="w-8 h-8 text-blue-400" />
                  </div>
                  <span className="text-xs font-mono text-zinc-200">
                    College_Major_Project_Template_2026.docx
                  </span>
                  <span className="text-[10px] text-zinc-500 mt-1">Ready for intake</span>
                </div>
              ) : (
                // Detected Sonar State
                <div className="flex flex-col items-center animate-fade-in">
                  <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-400 flex items-center justify-center mb-3 shadow-[0_0_30px_rgba(52,211,153,0.35)]">
                    <CheckCircle2 className="w-9 h-9 text-emerald-400" />
                  </div>
                  <span className="text-base font-semibold text-white">Template Detected</span>
                  <p className="text-xs text-emerald-400 font-mono mt-1 font-medium">
                    ARM understands your template.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 7: TEMPLATE ANALYSIS (Laser Scan Line + Active Tags)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 6 && (
          <div
            className="relative z-10 w-full max-w-2xl px-6 transition-all duration-700 ease-out"
            style={{
              transform: `scale(${0.96 + sceneProgress * 0.04}) translate3d(0, ${-sceneProgress * 6}px, 0)`,
            }}
          >
            <div className="text-center mb-5">
              <span className="text-xs font-mono uppercase tracking-widest text-emerald-400 font-semibold">
                Deep Document Inspection
              </span>
              <h3 className="text-2xl sm:text-3xl font-light text-white mt-1">Analyzing template...</h3>
            </div>

            {/* Document Wireframe with Real Laser Bar */}
            <div className="relative bg-zinc-950 border border-zinc-800 rounded-2xl p-6 shadow-2xl overflow-hidden backdrop-blur-md">
              {/* Laser Scan Line Sweeping Down */}
              <div
                className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-emerald-400 to-transparent shadow-[0_0_20px_#34d399] transition-all duration-150 pointer-events-none"
                style={{ top: `${sceneProgress * 92}%` }}
              />

              {/* Tag Badges: TEXT -> IMAGES -> LOGO -> BORDERS -> HEADER -> FOOTER -> LAYOUT */}
              <div className="flex flex-wrap gap-2 mb-4">
                {[
                  { label: "TEXT", active: sceneProgress > 0.1 },
                  { label: "IMAGES", active: sceneProgress > 0.22 },
                  { label: "LOGO", active: sceneProgress > 0.35 },
                  { label: "BORDERS", active: sceneProgress > 0.48 },
                  { label: "HEADER", active: sceneProgress > 0.6 },
                  { label: "FOOTER", active: sceneProgress > 0.72 },
                  { label: "LAYOUT", active: sceneProgress > 0.85 },
                ].map((tag) => (
                  <span
                    key={tag.label}
                    className={cn(
                      "px-2.5 py-1 rounded-md text-[10px] font-mono font-semibold transition-all duration-300",
                      tag.active
                        ? "bg-emerald-500/25 border border-emerald-400 text-emerald-300 shadow-[0_0_10px_rgba(52,211,153,0.3)] scale-105"
                        : "bg-zinc-900 border border-zinc-800 text-zinc-500"
                    )}
                  >
                    [{tag.label}]
                  </span>
                ))}
              </div>

              {/* Preserved Feature Rows */}
              <div className="space-y-2.5 font-mono text-xs">
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800">
                  <span className="text-zinc-200 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    College Header & Official Logo
                  </span>
                  <span className="text-emerald-400 text-[11px] font-bold">LOCKED</span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800">
                  <span className="text-zinc-200 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    Margins (1.25&quot; Left, 1.0&quot; Right) & Borders
                  </span>
                  <span className="text-emerald-400 text-[11px] font-bold">PRESERVED</span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800">
                  <span className="text-zinc-200 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    Fonts: Times New Roman 12pt / 1.5 Spacing
                  </span>
                  <span className="text-emerald-400 text-[11px] font-bold">PRESERVED</span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-zinc-850 flex items-center justify-between text-xs">
                <span className="text-zinc-400">Layout geometry:</span>
                <span className="font-semibold text-emerald-300">
                  Structure preserved 100%. No redesign.
                </span>
              </div>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 8: ADD EVIDENCE (Multimodal Floating Chips)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 7 && (
          <div
            className="relative z-10 w-full max-w-xl px-6 flex flex-col items-center transition-all duration-700 ease-out"
            style={{
              transform: `scale(${0.96 + sceneProgress * 0.04}) translate3d(${floatX * 0.3}px, ${floatY * 0.3}px, 0)`,
            }}
          >
            <h3 className="text-2xl sm:text-3xl font-light text-white mb-2 text-center">
              Add your project evidence
            </h3>
            <p className="text-xs text-zinc-400 mb-6 text-center">
              Connect real student artifacts directly to ARM.
            </p>

            <div className="w-full grid grid-cols-2 gap-3">
              {[
                {
                  fn: "soil_telemetry.csv",
                  info: "12,400 sensor readings",
                  color: "text-cyan-400",
                  ring: "ring-cyan-500/40",
                  icon: Database,
                  delay: 0.1,
                },
                {
                  fn: "irrigation_circuit.png",
                  info: "Hardware schematic",
                  color: "text-emerald-400",
                  ring: "ring-emerald-500/40",
                  icon: FileText,
                  delay: 0.3,
                },
                {
                  fn: "esp32_firmware.ino",
                  info: "Embedded edge C++",
                  color: "text-yellow-400",
                  ring: "ring-yellow-500/40",
                  icon: FileCode2,
                  delay: 0.5,
                },
                {
                  fn: "ieee_citations.bib",
                  info: "24 Peer-reviewed papers",
                  color: "text-purple-400",
                  ring: "ring-purple-500/40",
                  icon: Layers,
                  delay: 0.7,
                },
              ].map((item) => {
                const isRevealed = sceneProgress >= item.delay;
                const IconComponent = item.icon;
                return (
                  <div
                    key={item.fn}
                    className={cn(
                      "p-3.5 rounded-xl bg-zinc-900/90 border border-zinc-800 flex items-center gap-3 transition-all duration-500 shadow-md",
                      isRevealed
                        ? `scale-100 opacity-100 ring-1 ${item.ring}`
                        : "scale-90 opacity-30 translate-y-3"
                    )}
                  >
                    <IconComponent className={cn("w-5 h-5", item.color)} />
                    <div>
                      <p className="text-xs font-semibold text-white">{item.fn}</p>
                      <span className="text-[10px] text-zinc-400">{item.info}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 9: AI THINKING (Pulsing Neural Core + Moving Particles)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 8 && (
          <div
            className="relative z-10 w-full max-w-lg px-6 flex flex-col items-center transition-all duration-700 ease-out"
            style={{
              transform: `scale(${0.96 + sceneProgress * 0.04})`,
            }}
          >
            {/* Pulsing Synapse Orb */}
            <div className="relative w-24 h-24 mb-6 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full bg-emerald-500/15 animate-ping" />
              <div className="w-18 h-18 rounded-full border-2 border-emerald-400/60 bg-zinc-900/90 flex items-center justify-center shadow-[0_0_30px_rgba(52,211,153,0.3)]">
                <Cpu
                  className="w-9 h-9 text-emerald-400 animate-spin"
                  style={{ animationDuration: "7s" }}
                />
              </div>
            </div>

            {/* Stepped Thinking Phrases */}
            <div className="w-full bg-zinc-900/95 border border-zinc-800 rounded-2xl p-5 space-y-3 font-mono text-xs shadow-2xl backdrop-blur-xl">
              <div className="flex items-center gap-2.5 text-emerald-300">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>Thinking...</span>
              </div>
              <div
                className={cn(
                  "flex items-center gap-2.5 transition-all duration-500",
                  sceneProgress > 0.35
                    ? "opacity-100 text-zinc-200 translate-x-0"
                    : "opacity-20 text-zinc-600 -translate-x-2"
                )}
              >
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                <span>Understanding your project...</span>
              </div>
              <div
                className={cn(
                  "flex items-center gap-2.5 transition-all duration-500",
                  sceneProgress > 0.7
                    ? "opacity-100 text-emerald-300 font-semibold translate-x-0"
                    : "opacity-20 text-zinc-600 -translate-x-2"
                )}
              >
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>Creating your report...</span>
              </div>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 10: CONTENT REPLACEMENT (THE CORE HERO 3D SCENE)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 9 && (
          <div
            className="relative z-10 w-full max-w-4xl px-6 flex flex-col items-center transition-all duration-1000 ease-out"
            style={{
              transform: `perspective(1200px) rotateX(${6 - sceneProgress * 3}deg) rotateY(${
                -4 + sceneProgress * 3
              }deg) scale(${0.95 + sceneProgress * 0.05}) translate3d(${floatX * 0.3}px, ${floatY * 0.3}px, 0)`,
            }}
          >
            <div className="text-center mb-4">
              <h3 className="text-2xl sm:text-4xl font-light text-white tracking-tight">
                {sceneProgress < 0.4 ? (
                  "Replace content."
                ) : sceneProgress < 0.75 ? (
                  <>
                    Replace content.{" "}
                    <span className="font-semibold text-emerald-400">Preserve design.</span>
                  </>
                ) : (
                  <>
                    Replace content. Preserve design.{" "}
                    <span className="font-bold text-white underline decoration-emerald-400 underline-offset-4">
                      Automatically.
                    </span>
                  </>
                )}
              </h3>
            </div>

            {/* Tri-Stage Flow: OLD CONTENT -> ARM AI -> NEW PROJECT CONTENT */}
            <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-3.5 items-center">
              {/* Box 1: Old Content (Fades / Dissolves) */}
              <div className="p-4 rounded-xl bg-zinc-950 border border-red-500/30 text-xs relative shadow-lg">
                <span className="text-[10px] font-mono text-red-400 uppercase tracking-widest block mb-2 font-semibold">
                  1. Previous Senior Content
                </span>
                <p className="line-through text-zinc-500 font-medium">
                  &quot;Smart Home Automation System&quot;
                </p>
                <p className="line-through text-zinc-600 text-[11px] mt-1">
                  Chapter 3: Appliance relay control logic and legacy code...
                </p>
                <div className="mt-3 text-[10px] font-mono text-red-400/90 font-medium">
                  Dissolving out...
                </div>
              </div>

              {/* Box 2: ARM AI Engine */}
              <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/50 text-center flex flex-col items-center shadow-[0_0_25px_rgba(52,211,153,0.2)]">
                <div className="w-11 h-11 rounded-full bg-emerald-500/20 flex items-center justify-center mb-2">
                  <Cpu className="w-6 h-6 text-emerald-400 animate-pulse" />
                </div>
                <span className="text-xs font-bold text-white">ARM AI Core</span>
                <p className="text-[11px] text-zinc-300 mt-1">
                  Slot replacement with zero formatting shift
                </p>
              </div>

              {/* Box 3: New Project Content (Slots In) */}
              <div className="p-4 rounded-xl bg-zinc-950 border border-emerald-500/60 text-xs relative ring-1 ring-emerald-500/40 shadow-lg">
                <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-widest block mb-2 font-semibold">
                  2. New Project Content
                </span>
                <p className="text-white font-semibold text-sm">
                  &quot;AI Based Irrigation System&quot;
                </p>
                <p className="text-zinc-300 text-[11px] mt-1 leading-snug">
                  Chapter 3: Predictive moisture modeling and IoT edge dispatch...
                </p>
                <div className="mt-3 text-[10px] font-mono text-emerald-400 font-medium">
                  Inserted in exact font & margin
                </div>
              </div>
            </div>

            {/* Preserved Geometry Badges */}
            <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
              {[
                "Original Borders",
                "College Logos",
                "Headers & Footers",
                "Times New Roman 12pt",
                "Page Numbering",
                "Margins",
              ].map((item) => (
                <span
                  key={item}
                  className="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-[11px] font-mono text-zinc-300 flex items-center gap-1.5"
                >
                  <Check className="w-3 h-3 text-emerald-400" />
                  {item}: Preserved
                </span>
              ))}
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 11: BEFORE / AFTER (Animated Split Scan Wipe)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 10 && (
          <div
            className="relative z-10 w-full max-w-4xl px-6 flex flex-col items-center transition-all duration-700 ease-out"
            style={{
              transform: `scale(${0.96 + sceneProgress * 0.04})`,
            }}
          >
            <div className="text-center mb-4">
              <h3 className="text-2xl sm:text-3xl font-light text-white">
                Same template.{" "}
                <span className="font-semibold text-emerald-400">New project content.</span>
              </h3>
            </div>

            {/* Side by side comparison with moving divider wipe line */}
            <div className="w-full grid grid-cols-2 gap-4 bg-zinc-950 border border-zinc-800 rounded-2xl p-5 sm:p-6 relative shadow-2xl backdrop-blur-md">
              {/* Left Side: Original Template */}
              <div className="border border-zinc-800 rounded-xl p-4 bg-zinc-900/40">
                <div className="flex items-center justify-between pb-2 border-b border-zinc-800 mb-2">
                  <span className="text-[11px] font-mono uppercase text-zinc-400 font-semibold">
                    Original Template
                  </span>
                  <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">
                    Unmodified Layout
                  </span>
                </div>
                <div className="space-y-2 opacity-60">
                  <div className="w-16 h-3 bg-zinc-700 rounded" />
                  <div className="w-3/4 h-4 bg-zinc-600 rounded" />
                  <div className="w-full h-2 bg-zinc-800 rounded" />
                  <div className="w-5/6 h-2 bg-zinc-800 rounded" />
                </div>
              </div>

              {/* Right Side: ARM Generated Report */}
              <div className="border border-emerald-500/50 rounded-xl p-4 bg-emerald-950/15 ring-1 ring-emerald-500/30">
                <div className="flex items-center justify-between pb-2 border-b border-zinc-800 mb-2">
                  <span className="text-[11px] font-mono uppercase text-emerald-400 font-semibold">
                    ARM Generated Report
                  </span>
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded font-medium">
                    Verified
                  </span>
                </div>
                <div className="space-y-2">
                  <div className="w-16 h-3 bg-emerald-400/50 rounded" />
                  <p className="text-xs font-bold text-white">AI Based Irrigation System</p>
                  <p className="text-[11px] text-zinc-300 leading-tight">
                    Chapter 1: Autonomous soil moisture regulation with edge telemetry.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 12: REPORT GENERATION (DOCX & PDF Assembled)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 11 && (
          <div
            className="relative z-10 w-full max-w-xl px-6 flex flex-col items-center transition-all duration-700 ease-out"
            style={{
              transform: `scale(${0.96 + sceneProgress * 0.04}) translate3d(0, ${-sceneProgress * 5}px, 0)`,
            }}
          >
            <h3 className="text-3xl sm:text-4xl font-light text-white mb-1">Report ready.</h3>
            <p className="text-xs text-zinc-400 mb-6 font-mono">
              All styles, citations, and images compiled with 0 layout drift.
            </p>

            <div className="w-full grid grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-zinc-900 border border-blue-500/40 flex items-center gap-3 shadow-xl">
                <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center">
                  <FileCode2 className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-white">Project_Report.docx</p>
                  <span className="text-[10px] text-zinc-400">Microsoft Word • Editable</span>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-zinc-900 border border-red-500/40 flex items-center gap-3 shadow-xl">
                <div className="w-12 h-12 rounded-lg bg-red-500/20 flex items-center justify-center">
                  <FileText className="w-6 h-6 text-red-400" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-white">Project_Report.pdf</p>
                  <span className="text-[10px] text-zinc-400">Print Ready • Validated</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* -------------------------------------------------------------------
            SCENE 13: HERO FINALE (Cinematic Zoom & Direct Download Action)
            ------------------------------------------------------------------- */}
        {activeSceneIndex === 12 && (
          <div
            className="relative z-10 text-center px-6 max-w-3xl flex flex-col items-center transition-all duration-1000 ease-out"
            style={{
              transform: `scale(${0.96 + sceneProgress * 0.05}) translate3d(0, ${-sceneProgress * 6}px, 0)`,
            }}
          >
            <p className="text-xs font-mono uppercase tracking-[0.25em] text-zinc-400 mb-3">
              From college template... to complete project report.
            </p>

            <h1 className="text-6xl sm:text-8xl font-black tracking-tight text-white mb-2">ARM</h1>

            <p className="text-lg sm:text-xl font-light text-zinc-300 max-w-lg mb-6">
              Academic Report Made Intelligent
            </p>

            <div className="flex flex-wrap items-center justify-center gap-3">
              <Link
                href="/app"
                className="px-6 py-2.5 rounded-full bg-white text-black font-semibold text-sm hover:bg-zinc-200 transition-all flex items-center gap-2 shadow-xl hover:scale-105 active:scale-95"
              >
                Create. Analyze. Generate.
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="/ARM_Motion_Graphics.mp4"
                download="ARM_Motion_Graphics.mp4"
                className="px-5 py-2.5 rounded-full bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-all flex items-center gap-1.5 shadow-xl hover:scale-105 active:scale-95 cursor-pointer"
              >
                <Download className="w-3.5 h-3.5 stroke-[2.5]" />
                Download Video (.mp4)
              </a>
              <button
                onClick={restartVideo}
                className="px-4 py-2.5 rounded-full bg-zinc-900 border border-zinc-700 text-xs text-zinc-300 hover:text-white transition-all flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Replay Video
              </button>
            </div>
          </div>
        )}
      </div>

      {/* =====================================================================
          VIDEO OVERLAY CONTROLS BAR (Play/Pause, Scrubber, Audio, Scenes, MP4)
          ===================================================================== */}
      <div
        className={cn(
          "relative z-30 w-full bg-gradient-to-t from-black/95 via-black/80 to-transparent p-4 transition-opacity duration-300 flex flex-col gap-2",
          showControls ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
      >
        {/* Timeline Scrubber */}
        <div className="relative w-full h-2 bg-zinc-800 rounded-full cursor-pointer group flex items-center">
          <div
            className="absolute left-0 top-0 bottom-0 bg-emerald-400 rounded-full"
            style={{ width: `${(currentTime / TOTAL_DURATION) * 100}%` }}
          />

          {SCENES.map((scene, i) => (
            <div
              key={scene.id}
              onClick={(e) => {
                e.stopPropagation();
                jumpToScene(i);
              }}
              title={`${scene.title}: ${scene.subtitle}`}
              className={cn(
                "absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full cursor-pointer transition-transform hover:scale-150",
                currentTime >= scene.startTime ? "bg-emerald-300" : "bg-zinc-600"
              )}
              style={{ left: `${(scene.startTime / TOTAL_DURATION) * 100}%` }}
            />
          ))}

          <input
            type="range"
            min="0"
            max={TOTAL_DURATION}
            step="0.1"
            value={currentTime}
            onChange={(e) => setCurrentTime(parseFloat(e.target.value))}
            className="absolute inset-0 w-full opacity-0 cursor-pointer"
          />
        </div>

        {/* Action Controls Row */}
        <div className="flex items-center justify-between text-xs text-zinc-300 pt-1">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white transition-colors"
              title={isPlaying ? "Pause (Space)" : "Play (Space)"}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
            </button>

            <button
              onClick={restartVideo}
              className="p-1.5 rounded-lg hover:bg-zinc-900 text-zinc-400 hover:text-white transition-colors"
              title="Restart"
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            <span className="font-mono text-zinc-400 text-[11px]">
              {formatSeconds(currentTime)} / {formatSeconds(TOTAL_DURATION)}
            </span>

            <span className="text-zinc-600">|</span>

            <span className="font-mono text-[11px] text-emerald-400 font-medium">
              Scene {currentScene.id}/13: {currentScene.title}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Speed Toggle */}
            <button
              onClick={() => {
                const rates = [1, 1.25, 1.5, 0.75];
                const nextIdx = (rates.indexOf(playbackRate) + 1) % rates.length;
                setPlaybackRate(rates[nextIdx]);
              }}
              className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[11px] font-mono hover:text-white transition-colors"
              title="Playback Speed"
            >
              {playbackRate}x
            </button>

            {/* Audio Toggle */}
            <button
              onClick={toggleMute}
              className="p-1.5 rounded-lg hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors"
              title={isMuted ? "Unmute Audio (M)" : "Mute Audio (M)"}
            >
              {isMuted ? <VolumeX className="w-4 h-4 text-red-400" /> : <Volume2 className="w-4 h-4" />}
            </button>

            {/* Direct Download Video File (.mp4) */}
            <a
              href="/ARM_Motion_Graphics.mp4"
              download="ARM_Motion_Graphics.mp4"
              className="px-2.5 py-1 rounded-lg bg-zinc-900 hover:bg-emerald-500 hover:text-black border border-zinc-800 hover:border-emerald-400 text-zinc-300 transition-all flex items-center gap-1.5 text-[11px] font-mono cursor-pointer"
              title="Download ARM_Motion_Graphics.mp4"
            >
              <Download className="w-3.5 h-3.5" />
              <span>MP4</span>
            </a>

            {/* Fullscreen Toggle */}
            <button
              onClick={handleToggleFullscreen}
              className="p-1.5 rounded-lg hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors"
              title="Toggle Fullscreen (F)"
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
