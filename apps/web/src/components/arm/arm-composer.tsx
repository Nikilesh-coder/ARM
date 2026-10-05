"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Plus,
  ArrowUp,
  FileText,
  FileCode,
  Image as ImageIcon,
  Video,
  File,
  X,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface AttachedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  category: "document" | "pdf" | "image" | "video" | "code" | "other";
  status: "ready" | "uploading" | "error";
  file?: globalThis.File;
}

interface ArmComposerProps {
  onSendMessage: (text: string, attachments: AttachedFile[]) => void;
  isSubmitting?: boolean;
  placeholder?: string;
  className?: string;
}

export function ArmComposer({
  onSendMessage,
  isSubmitting = false,
  placeholder = "Ask ARM to synthesize your report, format an academic section, or analyze your template...",
  className,
}: ArmComposerProps) {
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<AttachedFile[]>([]);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileFilter, setFileFilter] = useState<string>("*");

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        220
      )}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleOpenFileSelector = (filter: string) => {
    setFileFilter(filter);
    setIsMenuOpen(false);
    setTimeout(() => {
      fileInputRef.current?.click();
    }, 50);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const newAttachments: AttachedFile[] = Array.from(files).map((file) => {
      let category: AttachedFile["category"] = "other";
      if (file.name.endsWith(".docx") || file.name.endsWith(".doc") || file.name.endsWith(".txt")) {
        category = "document";
      } else if (file.name.endsWith(".pdf")) {
        category = "pdf";
      } else if (file.type.startsWith("image/")) {
        category = "image";
      } else if (file.type.startsWith("video/")) {
        category = "video";
      } else if (file.name.endsWith(".py") || file.name.endsWith(".js") || file.name.endsWith(".ts") || file.name.endsWith(".json")) {
        category = "code";
      }

      return {
        id: Math.random().toString(36).substring(2, 9),
        name: file.name,
        size: file.size,
        type: file.type || "application/octet-stream",
        category,
        status: "ready",
        file,
      };
    });

    setAttachments((prev) => [...prev, ...newAttachments]);
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleRemoveAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  const hasUploading = attachments.some((a) => a.status === "uploading");
  const canSubmit = (input.trim().length > 0 || attachments.length > 0) && !isSubmitting && !hasUploading;

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSendMessage(input.trim(), attachments);
    setInput("");
    setAttachments([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className={cn("relative w-full max-w-4xl mx-auto", className)}>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={fileFilter}
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="relative rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950/90 shadow-xl backdrop-blur-md transition-all focus-within:border-zinc-400 dark:focus-within:border-zinc-700">
        {/* Attachment Chips Header */}
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 p-3 pb-0 max-h-36 overflow-y-auto border-b border-zinc-200 dark:border-zinc-900">
            {attachments.map((file) => {
              let Icon = File;
              if (file.category === "document") Icon = FileText;
              if (file.category === "pdf") Icon = FileText;
              if (file.category === "image") Icon = ImageIcon;
              if (file.category === "video") Icon = Video;
              if (file.category === "code") Icon = FileCode;

              return (
                <div
                  key={file.id}
                  className="flex items-center gap-2 pl-2.5 pr-1.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-800 dark:text-zinc-200"
                >
                  <Icon className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                  <span className="max-w-[140px] truncate font-mono text-[11px]">
                    {file.name}
                  </span>
                  <span className="text-[10px] text-zinc-500 font-mono">
                    {formatFileSize(file.size)}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleRemoveAttachment(file.id)}
                    className="p-1 rounded text-zinc-400 hover:text-zinc-700 dark:text-zinc-500 dark:hover:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors"
                    aria-label={`Remove ${file.name}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Text Area */}
        <div className="p-3 sm:p-4">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSubmitting}
            placeholder={placeholder}
            rows={1}
            className="w-full resize-none bg-transparent text-sm sm:text-base text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 dark:placeholder:text-zinc-500 focus:outline-none leading-relaxed min-h-[44px]"
          />
        </div>

        {/* Footer toolbar */}
        <div className="flex items-center justify-between px-3 sm:px-4 pb-3 pt-1">
          {/* Add / Attachment Menu */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsMenuOpen((prev) => !prev)}
              className="flex items-center justify-center w-8 h-8 rounded-full border border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors focus:outline-none"
              aria-label="Attach file"
            >
              <Plus className={cn("w-4 h-4 transition-transform", isMenuOpen && "rotate-45")} />
            </button>

            {/* Menu Popover */}
            {isMenuOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setIsMenuOpen(false)}
                />
                <div className="absolute bottom-11 left-0 z-50 w-56 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-1.5 shadow-2xl text-xs space-y-0.5">
                  <button
                    type="button"
                    onClick={() => handleOpenFileSelector(".docx,.doc,.txt")}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors"
                  >
                    <FileText className="w-4 h-4 text-blue-500" />
                    <span>Upload document (.docx)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleOpenFileSelector(".pdf")}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors"
                  >
                    <FileText className="w-4 h-4 text-red-500" />
                    <span>Upload PDF (.pdf)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleOpenFileSelector("image/*")}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors"
                  >
                    <ImageIcon className="w-4 h-4 text-emerald-500" />
                    <span>Upload image</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleOpenFileSelector("video/*")}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors"
                  >
                    <Video className="w-4 h-4 text-purple-500" />
                    <span>Upload video</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleOpenFileSelector("*")}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors"
                  >
                    <FileCode className="w-4 h-4 text-amber-500" />
                    <span>Upload other file (code/zip)</span>
                  </button>
                </div>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-zinc-400 dark:text-zinc-600 hidden sm:inline">
              Shift + Enter for new line
            </span>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSubmit}
              className={cn(
                "flex items-center justify-center w-8 h-8 rounded-full transition-all duration-200",
                canSubmit
                  ? "bg-zinc-900 text-white hover:bg-black dark:bg-white dark:text-black dark:hover:bg-zinc-200 active:scale-95 shadow-md"
                  : "bg-zinc-100 dark:bg-zinc-900 text-zinc-400 dark:text-zinc-600 cursor-not-allowed border border-zinc-200 dark:border-zinc-850"
              )}
              aria-label="Send message"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin text-zinc-400" />
              ) : (
                <ArrowUp className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
