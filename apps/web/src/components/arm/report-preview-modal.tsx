"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  X,
  FileText,
  Download,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Eye,
  ImageIcon,
  BookOpen,
  Check,
  Upload,
  Layers,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  FileCheck2,
  ChevronRight,
  ShieldCheck,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  apiClient,
  ReplacementJobResponseDTO,
  ReplacementStatsDTO,
} from "@/lib/api-client";

interface ReportPreviewModalProps {
  job: ReplacementJobResponseDTO | null;
  isOpen: boolean;
  onClose: () => void;
  onJobUpdated?: (updatedJob: ReplacementJobResponseDTO) => void;
}

const SECTION_OPTIONS = [
  { value: "abstract", label: "Abstract" },
  { value: "introduction", label: "Introduction" },
  { value: "objectives", label: "Project Objectives" },
  { value: "literature_review", label: "Literature Review" },
  { value: "methodology", label: "System Methodology & Architecture" },
  { value: "results", label: "Experimental Results & Discussion" },
  { value: "conclusion", label: "Conclusion" },
  { value: "future_scope", label: "Future Scope" },
  { value: "references", label: "References & Citations" },
];

const IMAGE_SLOTS = [
  { value: "image_1", label: "Cover College Logo (image_1)" },
  { value: "image_2", label: "System Architecture / Diagram (image_2)" },
  { value: "image_3", label: "Experimental Results Chart (image_3)" },
];

export function ReportPreviewModal({
  job: initialJob,
  isOpen,
  onClose,
  onJobUpdated,
}: ReportPreviewModalProps) {
  const [currentJob, setCurrentJob] = useState<ReplacementJobResponseDTO | null>(initialJob);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [isFullScreen, setIsFullScreen] = useState<boolean>(false);
  const [activePanel, setActivePanel] = useState<"document" | "sections" | "images">("document");

  // Regeneration state
  const [selectedSection, setSelectedSection] = useState<string>("methodology");
  const [sectionPrompt, setSectionPrompt] = useState<string>("");
  const [isRegeneratingSection, setIsRegeneratingSection] = useState<boolean>(false);

  // Image replacement state
  const [selectedSlot, setSelectedSlot] = useState<string>("image_2");
  const [imageCaption, setImageCaption] = useState<string>("");
  const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [isReplacingImage, setIsReplacingImage] = useState<boolean>(false);

  // Full regeneration & approval state
  const [isRegeneratingFull, setIsRegeneratingFull] = useState<boolean>(false);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setCurrentJob(initialJob);
    setFeedback(null);
  }, [initialJob]);

  if (!isOpen || !currentJob) return null;

  const stats: ReplacementStatsDTO = currentJob.stats || {};
  const isApproved = currentJob.approval_status === "approved";
  const validationStatus = stats.validation_status || "VALID";
  const pageCount = stats.page_count || 1;
  const wordCount = stats.estimated_word_count || 0;
  const sectionsList = stats.generated_sections || [];
  const imagesCount = currentJob.images_replaced || stats.images_count || 0;

  // Handler: Regenerate Full Report
  const handleRegenerateFull = async () => {
    try {
      setIsRegeneratingFull(true);
      setFeedback(null);
      const updated = await apiClient.regenerateReplacementReport(currentJob.job_id);
      setCurrentJob(updated);
      onJobUpdated?.(updated);
      setFeedback({ type: "success", text: "Full report successfully regenerated and replaced in-place!" });
    } catch (err: any) {
      setFeedback({ type: "error", text: `Full regeneration failed: ${err.message}` });
    } finally {
      setIsRegeneratingFull(false);
    }
  };

  // Handler: Regenerate Section
  const handleRegenerateSection = async () => {
    if (!selectedSection) return;
    try {
      setIsRegeneratingSection(true);
      setFeedback(null);
      const updated = await apiClient.regenerateReportSection({
        job_id: currentJob.job_id,
        section_name: selectedSection,
        custom_prompt: sectionPrompt.trim() || undefined,
      });
      setCurrentJob(updated);
      onJobUpdated?.(updated);
      setFeedback({
        type: "success",
        text: `Section '${selectedSection}' regenerated and updated in the template!`,
      });
      setSectionPrompt("");
    } catch (err: any) {
      setFeedback({ type: "error", text: `Section regeneration failed: ${err.message}` });
    } finally {
      setIsRegeneratingSection(false);
    }
  };

  // Handler: Image selection
  const handleImageFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImageFile(file);
      const reader = new FileReader();
      reader.onload = () => {
        setImagePreviewUrl(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  // Handler: Replace Image
  const handleReplaceImage = async () => {
    if (!selectedImageFile && !imagePreviewUrl) {
      setFeedback({ type: "error", text: "Please select an image file to upload." });
      return;
    }
    try {
      setIsReplacingImage(true);
      setFeedback(null);
      const updated = await apiClient.replaceReportImage({
        job_id: currentJob.job_id,
        image_slot: selectedSlot,
        image_base64: imagePreviewUrl || undefined,
        caption: imageCaption.trim() || undefined,
      });
      setCurrentJob(updated);
      onJobUpdated?.(updated);
      setFeedback({
        type: "success",
        text: `Image slot '${selectedSlot}' replaced with your selected asset!`,
      });
      setSelectedImageFile(null);
      setImagePreviewUrl(null);
      setImageCaption("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: any) {
      setFeedback({ type: "error", text: `Image replacement failed: ${err.message}` });
    } finally {
      setIsReplacingImage(false);
    }
  };

  // Handler: Approve Report
  const handleApproveReport = async () => {
    try {
      setIsApproving(true);
      setFeedback(null);
      const updated = await apiClient.approveReplacementReport(currentJob.job_id);
      setCurrentJob(updated);
      onJobUpdated?.(updated);
      setFeedback({
        type: "success",
        text: "Report Approved! Content is locked and ready for submission.",
      });
    } catch (err: any) {
      setFeedback({ type: "error", text: `Approval failed: ${err.message}` });
    } finally {
      setIsApproving(false);
    }
  };

  return (
    <div className={`fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex flex-col transition-all duration-300 ${isFullScreen ? "p-0" : "p-3 sm:p-6"}`}>
      <div className="flex-1 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl flex flex-col overflow-hidden shadow-2xl">
        
        {/* Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between px-6 py-3.5 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600/10 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                  ARM Report Preview
                </h2>
                {isApproved ? (
                  <Badge className="bg-emerald-600 text-white font-semibold flex items-center gap-1 text-[11px] py-0 px-2">
                    <CheckCircle2 className="w-3 h-3" /> Approved
                  </Badge>
                ) : (
                  <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 text-[11px] py-0 px-2">
                    Pending Approval
                  </Badge>
                )}
              </div>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                Master College Template In-Place Replacement • Zero layout distortion
              </p>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="px-2.5 py-1 rounded-md bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 font-medium">
              📄 {pageCount} {pageCount === 1 ? "Page" : "Pages"}
            </div>
            <div className="px-2.5 py-1 rounded-md bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 font-medium">
              📝 {wordCount.toLocaleString()} Words
            </div>
            <div className="px-2.5 py-1 rounded-md bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 font-medium">
              📑 {sectionsList.length || 8} Sections
            </div>
            <div className="px-2.5 py-1 rounded-md bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 font-medium">
              🖼️ {imagesCount} Figures
            </div>
            <Badge
              className={
                validationStatus === "VALID"
                  ? "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300"
                  : "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300"
              }
            >
              {validationStatus === "VALID" ? "✓ Structure Valid" : "⚠ Minor Warning"}
            </Badge>

            {/* Window Controls */}
            <div className="flex items-center space-x-1 pl-2 border-l border-zinc-300 dark:border-zinc-700">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-zinc-500"
                onClick={() => setZoomLevel((z) => Math.max(70, z - 10))}
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </Button>
              <span className="text-[11px] font-mono text-zinc-500 min-w-8 text-center">{zoomLevel}%</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-zinc-500"
                onClick={() => setZoomLevel((z) => Math.min(150, z + 10))}
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-zinc-500"
                onClick={() => setIsFullScreen(!isFullScreen)}
                title={isFullScreen ? "Restore" : "Full Screen"}
              >
                {isFullScreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
                onClick={onClose}
                title="Close"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Action Toolbar */}
        <div className="px-6 py-2.5 bg-zinc-100 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-1.5">
            <Button
              variant={activePanel === "document" ? "primary" : "outline"}
              size="sm"
              onClick={() => setActivePanel("document")}
              className="text-xs h-8"
            >
              <Eye className="w-3.5 h-3.5 mr-1.5" /> Document Preview
            </Button>
            <Button
              variant={activePanel === "sections" ? "primary" : "outline"}
              size="sm"
              onClick={() => setActivePanel("sections")}
              className="text-xs h-8"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Regenerate Section
            </Button>
            <Button
              variant={activePanel === "images" ? "primary" : "outline"}
              size="sm"
              onClick={() => setActivePanel("images")}
              className="text-xs h-8"
            >
              <ImageIcon className="w-3.5 h-3.5 mr-1.5" /> Replace Image
            </Button>
          </div>

          <div className="flex items-center gap-2">
            {/* 1. Full Regenerate */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleRegenerateFull}
              disabled={isRegeneratingFull || isApproved}
              className="text-xs h-8"
              title="Regenerate all sections"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isRegeneratingFull ? "animate-spin" : ""}`} />
              {isRegeneratingFull ? "Regenerating..." : "Regenerate All"}
            </Button>

            {/* 4. Approve Report */}
            {!isApproved ? (
              <Button
                size="sm"
                onClick={handleApproveReport}
                disabled={isApproving}
                className="text-xs h-8 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
              >
                <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />
                {isApproving ? "Approving..." : "Approve Report"}
              </Button>
            ) : (
              <div className="flex items-center text-xs font-semibold text-emerald-600 dark:text-emerald-400 px-2 py-1 bg-emerald-50 dark:bg-emerald-950/40 rounded border border-emerald-200 dark:border-emerald-800">
                <Lock className="w-3 h-3 mr-1" /> Approved & Locked
              </div>
            )}

            {/* 5. Download DOCX */}
            <a
              href={apiClient.getReplacementDownloadUrl(currentJob.job_id, "docx")}
              download
              className="inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 text-xs h-8 px-3 bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Download DOCX
            </a>
          </div>
        </div>

        {/* Feedback Banner */}
        {feedback && (
          <div
            className={`px-6 py-2.5 text-xs flex items-center justify-between border-b ${
              feedback.type === "success"
                ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800"
                : "bg-rose-50 dark:bg-rose-950/30 text-rose-800 dark:text-rose-300 border-rose-200 dark:border-rose-800"
            }`}
          >
            <div className="flex items-center gap-2">
              {feedback.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-600" />
              )}
              <span>{feedback.text}</span>
            </div>
            <button
              onClick={() => setFeedback(null)}
              className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-xs font-bold"
            >
              ✕
            </button>
          </div>
        )}

        {/* Main Body Layout */}
        <div className="flex-1 flex overflow-hidden">
          {/* Action Drawer: Regenerate Section */}
          {activePanel === "sections" && (
            <div className="w-80 sm:w-96 border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/40 p-5 overflow-y-auto space-y-4">
              <div>
                <h3 className="text-sm font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 text-blue-500" /> Targeted Section Regeneration
                </h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                  Regenerate an individual section via AI and automatically re-insert it into the master template.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Select Section to Refine:
                </label>
                <select
                  value={selectedSection}
                  onChange={(e) => setSelectedSection(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {SECTION_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Refinement Prompt / Guidance (Optional):
                </label>
                <textarea
                  value={sectionPrompt}
                  onChange={(e) => setSectionPrompt(e.target.value)}
                  rows={4}
                  placeholder="e.g. Include specific metrics for accuracy, latency, and hardware constraints. Emphasize IoT edge device comparisons."
                  className="w-full text-xs px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <Button
                onClick={handleRegenerateSection}
                disabled={isRegeneratingSection || isApproved}
                className="w-full text-xs bg-blue-600 hover:bg-blue-700 text-white"
              >
                <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isRegeneratingSection ? "animate-spin" : ""}`} />
                {isRegeneratingSection ? "Regenerating Section..." : "Regenerate & Update In-Place"}
              </Button>
            </div>
          )}

          {/* Action Drawer: Replace Image */}
          {activePanel === "images" && (
            <div className="w-80 sm:w-96 border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/40 p-5 overflow-y-auto space-y-4">
              <div>
                <h3 className="text-sm font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                  <ImageIcon className="w-4 h-4 text-purple-500" /> In-Place Image Replacement
                </h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                  Swap out any template figure with a custom diagram, circuit schematic, or college logo.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Target Template Slot:
                </label>
                <select
                  value={selectedSlot}
                  onChange={(e) => setSelectedSlot(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  {IMAGE_SLOTS.map((slot) => (
                    <option key={slot.value} value={slot.value}>
                      {slot.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Upload Replacement Image:
                </label>
                <input
                  type="file"
                  accept="image/png, image/jpeg, image/jpg, image/webp"
                  ref={fileInputRef}
                  onChange={handleImageFileChange}
                  className="w-full text-xs text-zinc-500 file:mr-2 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100 dark:file:bg-purple-950 dark:file:text-purple-300 cursor-pointer"
                />
              </div>

              {imagePreviewUrl && (
                <div className="p-2 border border-zinc-200 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800">
                  <span className="text-[10px] text-zinc-400 font-mono block mb-1">Image Preview:</span>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imagePreviewUrl}
                    alt="Preview to upload"
                    className="max-h-36 mx-auto object-contain rounded"
                  />
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Figure Caption:
                </label>
                <input
                  type="text"
                  value={imageCaption}
                  onChange={(e) => setImageCaption(e.target.value)}
                  placeholder="e.g. Fig. 2. Convolutional neural network classification pipeline"
                  className="w-full text-xs px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <Button
                onClick={handleReplaceImage}
                disabled={isReplacingImage || (!selectedImageFile && !imagePreviewUrl) || isApproved}
                className="w-full text-xs bg-purple-600 hover:bg-purple-700 text-white"
              >
                <Upload className={`w-3.5 h-3.5 mr-1.5 ${isReplacingImage ? "animate-spin" : ""}`} />
                {isReplacingImage ? "Embedding Image..." : "Replace & Re-insert Image"}
              </Button>
            </div>
          )}

          {/* Central Report Reading Viewport */}
          <div className="flex-1 bg-zinc-100 dark:bg-zinc-900/90 overflow-y-auto p-4 sm:p-8 flex justify-center">
            <div
              style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: "top center" }}
              className="transition-transform duration-200 w-full max-w-4xl"
            >
              {currentJob.preview_html ? (
                <div
                  className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-2xl rounded-xl p-8 sm:p-12 border border-zinc-200 dark:border-zinc-800 transition-colors"
                  dangerouslySetInnerHTML={{ __html: currentJob.preview_html }}
                />
              ) : (
                <div className="p-12 text-center text-zinc-500 bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700">
                  <FileText className="w-12 h-12 mx-auto text-zinc-400 mb-3" />
                  <p className="text-sm font-semibold">Preview HTML is being compiled...</p>
                  <p className="text-xs text-zinc-400 mt-1">
                    The document was generated. You can download the completed DOCX directly.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
