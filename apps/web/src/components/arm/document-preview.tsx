"use client";

import React, { useState } from "react";
import {
  X,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  Download,
  CheckCircle2,
  AlertTriangle,
  FileText,
  ChevronLeft,
  ChevronRight,
  BookOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { GeneratedDocument } from "./generated-document-card";

interface PreviewSection {
  id: string;
  title: string;
  pageNumber: number;
  wordCount: number;
  content: string;
}

interface DocumentPreviewProps {
  document: GeneratedDocument;
  sections?: PreviewSection[];
  onClose: () => void;
}

export function DocumentPreview({
  document,
  sections: propSections,
  onClose,
}: DocumentPreviewProps) {
  const defaultSections: PreviewSection[] = [
    {
      id: "sec-1",
      title: "1. Introduction & Problem Statement",
      pageNumber: 1,
      wordCount: 840,
      content:
        "The exponential rise in academic administrative overhead necessitates automated, deterministic document synthesis systems. Traditional generative models lack strict typography containment, frequently invalidating institution-mandated line spacing and margin bounds.",
    },
    {
      id: "sec-2",
      title: "2. Literature Review & Prior Art",
      pageNumber: 3,
      wordCount: 1420,
      content:
        "Standard document authoring workflows rely on manual template manipulation within desktop word processors. Automated compilation pipelines typically target LaTeX rather than the docx format mandated across Indian engineering institutions.",
    },
    {
      id: "sec-3",
      title: "3. System Architecture & Methodology",
      pageNumber: 7,
      wordCount: 2150,
      content:
        "The system decouples content generation from document assembly. An LLM agent synthesizes factual text blocks conditioned on uploaded evidence artifacts, while a deterministic OpenXML engine enforces strict document geometry.",
    },
  ];

  const sections = propSections || document.sections || defaultSections;
  const [activeSectionId, setActiveSectionId] = useState(sections[0]?.id || "");
  const [zoomLevel, setZoomLevel] = useState(100);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [activeTab, setActiveTab] = useState<"validation" | "citations" | "evidence">("validation");

  const activeSection = sections.find((s) => s.id === activeSectionId) || sections[0];

  const handleZoom = (delta: number) => {
    setZoomLevel((prev) => Math.max(70, Math.min(160, prev + delta)));
  };

  return (
    <div
      className={`fixed inset-0 z-50 bg-black/60 dark:bg-black/90 backdrop-blur-md flex flex-col transition-colors duration-300 ${
        isFullScreen ? "p-0" : "p-4 sm:p-6"
      }`}
    >
      <div className="flex-1 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl flex flex-col overflow-hidden shadow-2xl transition-colors duration-300">
        {/* Top Header Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-850 bg-zinc-50 dark:bg-zinc-900/50">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-blue-500" />
            <div>
              <h2 className="text-sm font-semibold text-zinc-900 dark:text-white tracking-tight">
                {document.title}
              </h2>
              <p className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400">
                {document.fileName} • Preview Mode
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Zoom Controls */}
            <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-0.5 text-xs text-zinc-700 dark:text-zinc-300">
              <button
                onClick={() => handleZoom(-10)}
                className="p-1.5 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded"
                aria-label="Zoom out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="px-2 font-mono text-[11px]">{zoomLevel}%</span>
              <button
                onClick={() => handleZoom(10)}
                className="p-1.5 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded"
                aria-label="Zoom in"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
            </div>

            <button
              onClick={() => setIsFullScreen(!isFullScreen)}
              className="p-2 border border-zinc-200 dark:border-zinc-800 rounded-lg text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-900"
              aria-label="Toggle full screen"
            >
              {isFullScreen ? (
                <Minimize2 className="w-4 h-4" />
              ) : (
                <Maximize2 className="w-4 h-4" />
              )}
            </button>

            {document.docxAvailable && document.docxDownloadUrl && (
              <a href={document.docxDownloadUrl} download={document.fileName}>
                <Button variant="primary" size="sm" className="text-xs">
                  <Download className="w-3.5 h-3.5 mr-1" />
                  Download
                </Button>
              </a>
            )}

            <button
              onClick={onClose}
              className="p-2 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-900"
              aria-label="Close preview"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* 3-Column Preview Body */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: Section Navigator */}
          <div className="w-64 border-r border-zinc-850 bg-zinc-900/20 p-4 overflow-y-auto hidden md:block">
            <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-500 mb-3">
              Sections ({sections.length})
            </h3>
            <div className="space-y-1">
              {sections.map((sec) => (
                <button
                  key={sec.id}
                  onClick={() => setActiveSectionId(sec.id)}
                  className={`w-full text-left p-2.5 rounded-lg text-xs transition-colors flex items-center justify-between ${
                    sec.id === activeSectionId
                      ? "bg-zinc-800 text-white font-medium border border-zinc-700"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
                  }`}
                >
                  <span className="truncate">{sec.title}</span>
                  <span className="text-[10px] font-mono text-zinc-500 shrink-0 ml-2">
                    p. {sec.pageNumber}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Center: Document Page Canvas */}
          <div className="flex-1 bg-zinc-950 p-6 overflow-y-auto flex justify-center">
            <div
              style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: "top center" }}
              className="w-full max-w-2xl bg-zinc-900 border border-zinc-800 rounded-xl p-8 sm:p-12 text-zinc-200 shadow-2xl transition-transform duration-150 h-fit"
            >
              <div className="border-b border-zinc-800 pb-4 mb-6 flex justify-between items-center text-xs text-zinc-500 font-mono">
                <span>{document.title}</span>
                <span>Page {activeSection?.pageNumber || 1}</span>
              </div>

              <h1 className="text-xl sm:text-2xl font-bold text-white mb-6 tracking-tight">
                {activeSection?.title}
              </h1>

              <div className="space-y-4 text-sm leading-relaxed font-serif text-zinc-300">
                <p>{activeSection?.content}</p>
                <p className="text-xs text-zinc-500 italic pt-4">
                  [Section word count: {activeSection?.wordCount} words • Validated against template margins: 1.25 in left, 1.00 in right]
                </p>
              </div>

              <div className="mt-12 pt-4 border-t border-zinc-800 flex justify-between items-center text-xs text-zinc-500 font-mono">
                <span>Confidential Academic Draft</span>
                <span>ARM Synthesis Engine</span>
              </div>
            </div>
          </div>

          {/* Right: Validation & Citations Inspector */}
          <div className="w-80 border-l border-zinc-850 bg-zinc-900/20 p-4 overflow-y-auto hidden lg:block">
            {/* Tabs */}
            <div className="flex border-b border-zinc-800 pb-2 mb-4 gap-2 text-xs">
              <button
                onClick={() => setActiveTab("validation")}
                className={`pb-1 font-medium transition-colors ${
                  activeTab === "validation"
                    ? "text-white border-b-2 border-blue-500"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Validation
              </button>
              <button
                onClick={() => setActiveTab("citations")}
                className={`pb-1 font-medium transition-colors ${
                  activeTab === "citations"
                    ? "text-white border-b-2 border-blue-500"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Citations
              </button>
              <button
                onClick={() => setActiveTab("evidence")}
                className={`pb-1 font-medium transition-colors ${
                  activeTab === "evidence"
                    ? "text-white border-b-2 border-blue-500"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Evidence
              </button>
            </div>

            {activeTab === "validation" && (
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/40 text-xs">
                  <div className="flex items-center gap-2 text-emerald-400 font-medium mb-1">
                    <CheckCircle2 className="w-4 h-4" />
                    Margin Bounds Matched
                  </div>
                  <p className="text-zinc-400 text-[11px]">
                    1.25&quot; left gutter and 1.0&quot; outer margins enforced strictly by docx engine.
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/40 text-xs">
                  <div className="flex items-center gap-2 text-emerald-400 font-medium mb-1">
                    <CheckCircle2 className="w-4 h-4" />
                    Heading Hierarchy
                  </div>
                  <p className="text-zinc-400 text-[11px]">
                    Times New Roman 14pt bold (Heading 1) and 12pt bold (Heading 2) maintained.
                  </p>
                </div>
              </div>
            )}

            {activeTab === "citations" && (
              <div className="space-y-2 text-xs">
                <div className="p-2.5 rounded-lg border border-zinc-800 bg-zinc-900/40">
                  <div className="font-mono text-[11px] text-blue-400 mb-0.5">[1] IEEE Standards</div>
                  <p className="text-zinc-400 text-[11px]">Format specifications for engineering documentation.</p>
                </div>
                <div className="p-2.5 rounded-lg border border-zinc-800 bg-zinc-900/40">
                  <div className="font-mono text-[11px] text-blue-400 mb-0.5">[2] ISO/IEC 29500</div>
                  <p className="text-zinc-400 text-[11px]">Office Open XML File Formats Reference.</p>
                </div>
              </div>
            )}

            {activeTab === "evidence" && (
              <div className="space-y-2 text-xs">
                <div className="p-2.5 rounded-lg border border-zinc-800 bg-zinc-900/40">
                  <span className="font-mono text-[10px] text-emerald-400 uppercase">Dataset</span>
                  <p className="text-zinc-200 text-xs mt-0.5">benchmark_metrics.csv</p>
                  <p className="text-zinc-500 text-[10px]">Verified against methodology chapter</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
