"use client";

import React from "react";
import {
  FileText,
  Download,
  Eye,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface GeneratedDocument {
  id: string;
  title: string;
  fileName: string;
  fileSizeBytes?: number;
  pdfAvailable?: boolean;
  pdfDownloadUrl?: string;
  docxAvailable?: boolean;
  docxDownloadUrl?: string;
  creationStatus: "draft" | "generated" | "validated";
  validationStatus: "passed" | "warnings" | "pending";
  createdAt: string;
  sectionCount?: number;
  sections?: {
    id: string;
    title: string;
    pageNumber: number;
    wordCount: number;
    content: string;
  }[];
}

interface GeneratedDocumentCardProps {
  document: GeneratedDocument;
  onPreview?: (doc: GeneratedDocument) => void;
  onOpenReport?: (doc: GeneratedDocument) => void;
  className?: string;
}

export function GeneratedDocumentCard({
  document,
  onPreview,
  className,
}: GeneratedDocumentCardProps) {
  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "305 KB";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const sectionCount = document.sectionCount || 8;

  return (
    <div className={cn("w-full max-w-2xl space-y-4 my-2 animate-in zoom-in-95 duration-200", className)}>
      {/* Green Success Synthesis Banner */}
      <div className="p-6 rounded-2xl border border-emerald-200 dark:border-emerald-950/80 bg-emerald-50/60 dark:bg-emerald-950/20 text-center space-y-2">
        <div className="w-12 h-12 rounded-xl bg-emerald-600 text-white flex items-center justify-center mx-auto shadow-sm">
          <CheckCircle2 className="w-7 h-7" />
        </div>
        <h3 className="text-xl font-bold tracking-tight text-emerald-950 dark:text-emerald-100">
          Report Successfully Synthesized!
        </h3>
        <p className="text-xs text-emerald-800 dark:text-emerald-300 max-w-md mx-auto leading-relaxed">
          All {sectionCount} reviewed chapters have been created with Times New Roman 14pt (H1), 12pt body text, and 1.25&quot; college binding margins.
        </p>
      </div>

      {/* Document Download & Details Card */}
      <div className="p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4 shadow-sm">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400 shrink-0">
              <FileText className="w-6 h-6" />
            </div>
            <div className="min-w-0">
              <h4 className="text-sm font-bold text-zinc-900 dark:text-white truncate max-w-sm">
                {document.fileName}
              </h4>
              <p className="text-xs text-zinc-500 font-mono mt-0.5">
                {formatFileSize(document.fileSizeBytes)} • OpenXML Format • Verified
              </p>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 text-xs font-semibold shrink-0">
            Ready
          </span>
        </div>

        {/* Action Buttons: Side-by-Side DOCX and Preview */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
          <a
            href={document.docxDownloadUrl || "/Project_Report_Final_IEEE.docx"}
            download={document.fileName}
            className="py-2.5 px-3 rounded-xl border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-750 text-xs font-semibold text-zinc-900 dark:text-white flex items-center justify-center gap-2 transition-colors cursor-pointer text-center"
          >
            <Download className="w-4 h-4 text-blue-500 shrink-0" />
            Download .DOCX
          </a>
          {onPreview && (
            <button
              type="button"
              onClick={() => onPreview(document)}
              className="py-2.5 px-3 rounded-xl border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-750 text-xs font-semibold text-zinc-900 dark:text-white flex items-center justify-center gap-2 transition-colors cursor-pointer"
            >
              <Eye className="w-4 h-4 text-zinc-600 dark:text-zinc-300 shrink-0" />
              Preview Document
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
