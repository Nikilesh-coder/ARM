"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Lock,
  Unlock,
  ShieldCheck,
  Type,
  Layers,
  Save,
  X,
  AlertTriangle,
  Info,
  Calendar,
  User,
  Sliders
} from "lucide-react";

interface TemplateReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  templateId: string;
  templateName: string;
  isInitiallyLocked?: boolean;
  onLockSuccess?: (lockedData: any) => void;
}

const CANONICAL_ROLES = [
  "TITLE_PAGE",
  "CERTIFICATE",
  "DECLARATION",
  "ACKNOWLEDGEMENT",
  "ABSTRACT",
  "TOC",
  "LIST_OF_FIGURES",
  "LIST_OF_TABLES",
  "INTRODUCTION",
  "LITERATURE_REVIEW",
  "METHODOLOGY",
  "SYSTEM_DESIGN",
  "IMPLEMENTATION",
  "RESULTS",
  "DISCUSSION",
  "CONCLUSION",
  "FUTURE_WORK",
  "REFERENCES",
  "APPENDIX",
  "CUSTOM_SECTION",
];

export function TemplateReviewModal({
  isOpen,
  onClose,
  projectId,
  templateId,
  templateName,
  isInitiallyLocked = false,
  onLockSuccess,
}: TemplateReviewModalProps) {
  const [reviewData, setReviewData] = useState<any | null>(null);
  const [sections, setSections] = useState<any[]>([]);
  const [isLocked, setIsLocked] = useState<boolean>(isInitiallyLocked);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isLocking, setIsLocking] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showLockConfirm, setShowLockConfirm] = useState<boolean>(false);

  const fetchReview = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await apiClient.getProjectTemplateReview(projectId, templateId);
      setReviewData(data);
      setIsLocked(data.is_locked || false);

      const activeSchema = data.reviewed_schema || data.source_analysis || {};
      const activeSections = activeSchema.sections || [];
      setSections(JSON.parse(JSON.stringify(activeSections)));
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load template review.");
    } finally {
      setIsLoading(false);
    }
  }, [projectId, templateId]);

  useEffect(() => {
    if (isOpen) {
      fetchReview();
    }
  }, [isOpen, fetchReview]);

  // Keyboard accessibility: Escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (showLockConfirm) {
          setShowLockConfirm(false);
        } else {
          onClose();
        }
      }
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, showLockConfirm, onClose]);

  if (!isOpen) return null;

  const handleSectionChange = (index: number, field: string, value: any) => {
    if (isLocked) return;
    const updated = [...sections];
    updated[index] = { ...updated[index], [field]: value };
    setSections(updated);
  };

  const handleSaveDraft = async () => {
    if (isLocked) return;
    setIsSaving(true);
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      const currentSchema = reviewData?.reviewed_schema || reviewData?.source_analysis || {};
      const updatedSchema = {
        ...currentSchema,
        sections: sections.map((s, idx) => ({
          ...s,
          order: idx + 1,
        })),
      };

      const res = await apiClient.patchProjectTemplateReview(projectId, templateId, {
        reviewed_schema: updatedSchema,
        notes: "Student manual adjustments",
      });

      setReviewData(res);
      setStatusMessage("Review draft saved successfully.");
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to save review draft.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleConfirmLock = async () => {
    setIsLocking(true);
    setErrorMessage(null);

    try {
      // First save draft if any modifications were made
      const currentSchema = reviewData?.reviewed_schema || reviewData?.source_analysis || {};
      const updatedSchema = {
        ...currentSchema,
        sections: sections.map((s, idx) => ({
          ...s,
          order: idx + 1,
        })),
      };

      await apiClient.patchProjectTemplateReview(projectId, templateId, {
        reviewed_schema: updatedSchema,
      });

      const lockRes = await apiClient.lockProjectTemplate(projectId, templateId, {
        confirm: true,
        notes: "Confirmed and locked by student",
      });

      setIsLocked(true);
      setShowLockConfirm(false);
      setStatusMessage("Template locked successfully! It is now the authoritative formatting source of truth.");
      onLockSuccess?.(lockRes);
      await fetchReview();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to lock template.");
      setShowLockConfirm(false);
    } finally {
      setIsLocking(false);
    }
  };

  const sourceSchema = reviewData?.source_analysis || {};
  const geometry = sourceSchema.geometry || {};
  const typography = sourceSchema.typography || {};
  const margins = geometry.margins || {};

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/70 backdrop-blur-sm animate-in fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="template-review-title"
    >
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950/50">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isLocked ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400" : "bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400"}`}>
              {isLocked ? <Lock className="w-5 h-5" /> : <Sliders className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="template-review-title" className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                  Template Review & Authorization
                </h2>
                {isLocked ? (
                  <Badge variant="outline" className="bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800 text-[10px] font-semibold flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3" />
                    LOCKED (AUTHORITATIVE)
                  </Badge>
                ) : (
                  <Badge variant="outline" className="bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-800 text-[10px] font-semibold">
                    READY FOR REVIEW
                  </Badge>
                )}
              </div>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                Template: <span className="font-semibold text-zinc-700 dark:text-zinc-300">{templateName}</span> &bull; Source file remains completely immutable.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            aria-label="Close review dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status / Alert Banners */}
        <div aria-live="polite">
          {isLocked && (
            <div className="px-6 py-2.5 bg-emerald-50/80 dark:bg-emerald-950/30 border-b border-emerald-200 dark:border-emerald-800/60 flex items-center justify-between text-xs text-emerald-900 dark:text-emerald-200">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>
                  <b>Authoritative Source of Truth:</b> This template is locked. Report planning and document assembly will adhere strictly to this reviewed structure.
                </span>
              </div>
              {reviewData?.locked_at && (
                <div className="flex items-center gap-3 text-[11px] text-emerald-700 dark:text-emerald-300 font-mono">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(reviewData.locked_at).toLocaleDateString()}
                  </span>
                  <span>v{reviewData.locked_schema_version || "1.0.0"}</span>
                </div>
              )}
            </div>
          )}

          {statusMessage && (
            <div className="px-6 py-2 bg-blue-50 dark:bg-blue-950/40 border-b border-blue-200 dark:border-blue-800 flex items-center gap-2 text-xs text-blue-700 dark:text-blue-300">
              <CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0" />
              <span>{statusMessage}</span>
            </div>
          )}

          {errorMessage && (
            <div className="px-6 py-2 bg-rose-50 dark:bg-rose-950/40 border-b border-rose-200 dark:border-rose-800 flex items-center gap-2 text-xs text-rose-700 dark:text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading ? (
            <div className="py-16 flex flex-col items-center justify-center gap-3 text-zinc-400">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              <p className="text-xs">Loading template analysis data...</p>
            </div>
          ) : (
            <>
              {/* Document Overview & Page Format */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Document Facts */}
                <div className="bg-zinc-50 dark:bg-zinc-950/60 p-4 rounded-lg border border-zinc-200 dark:border-zinc-800 space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-semibold text-zinc-900 dark:text-zinc-100 border-b border-zinc-200/80 dark:border-zinc-800/80 pb-1.5">
                    <FileText className="w-3.5 h-3.5 text-zinc-500" />
                    Document Source Facts
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-zinc-400 text-[10px] uppercase font-mono block">Format</span>
                      <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                        {reviewData?.file_type?.toUpperCase() || "DOCX"}
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-400 text-[10px] uppercase font-mono block">Page Count</span>
                      <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                        {sourceSchema.document?.page_count || 1} pages
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-400 text-[10px] uppercase font-mono block">Page Size</span>
                      <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                        {geometry.page_size || "A4"} ({geometry.orientation || "portrait"})
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-400 text-[10px] uppercase font-mono block">Margins (T/B/L/R)</span>
                      <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                        {margins.top_mm ? `${margins.top_mm} / ${margins.bottom_mm} / ${margins.left_mm} / ${margins.right_mm} mm` : "Standard"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Typography Rules */}
                <div className="bg-zinc-50 dark:bg-zinc-950/60 p-4 rounded-lg border border-zinc-200 dark:border-zinc-800 space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-semibold text-zinc-900 dark:text-zinc-100 border-b border-zinc-200/80 dark:border-zinc-800/80 pb-1.5">
                    <Type className="w-3.5 h-3.5 text-zinc-500" />
                    Typography & Spacing Rules
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-zinc-400 text-[10px] uppercase font-mono block">Body Font</span>
                      <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                        {typography.default_font || "Times New Roman"} ({typography.default_size_pt || 12} pt)
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-400 text-[10px] uppercase font-mono block">Line Spacing</span>
                      <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                        {typography.line_spacing || 1.5}x ({typography.alignment || "justify"})
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-400 text-[10px] uppercase font-mono block">Heading 1</span>
                      <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                        {typography.headings?.level_1 ? `${typography.headings.level_1.font_name}, ${typography.headings.level_1.size_pt}pt` : "14 pt Bold"}
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-400 text-[10px] uppercase font-mono block">Heading 2</span>
                      <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                        {typography.headings?.level_2 ? `${typography.headings.level_2.font_name}, ${typography.headings.level_2.size_pt}pt` : "13 pt Bold"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Sections Review Table */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Layers className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-700 dark:text-zinc-300">
                      Document Structure & Hierarchy ({sections.length} Sections)
                    </h3>
                  </div>
                  {!isLocked && (
                    <span className="text-[11px] text-zinc-400">
                      Review semantic roles, titles, and hierarchy levels below before locking.
                    </span>
                  )}
                </div>

                <div className="border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-zinc-100/80 dark:bg-zinc-950 font-semibold text-zinc-700 dark:text-zinc-300 border-b border-zinc-200 dark:border-zinc-800">
                        <tr>
                          <th className="py-2.5 px-3 w-12 text-center">#</th>
                          <th className="py-2.5 px-3 w-20">Level</th>
                          <th className="py-2.5 px-3 min-w-[180px]">Detected Title</th>
                          <th className="py-2.5 px-3 min-w-[180px]">Semantic Role</th>
                          <th className="py-2.5 px-3 w-28">Numbering</th>
                          <th className="py-2.5 px-3 w-32 text-center">Confidence</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                        {sections.map((sec, idx) => {
                          const confScore = sec.confidence ?? 0.8;
                          const confLabel =
                            confScore >= 0.8 ? "High confidence" : confScore >= 0.5 ? "Medium confidence" : "Needs review";
                          const confBadgeColor =
                            confScore >= 0.8
                              ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border-emerald-300"
                              : confScore >= 0.5
                              ? "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border-blue-300"
                              : "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border-amber-300";

                          return (
                            <tr
                              key={sec.id || idx}
                              className="hover:bg-zinc-50/50 dark:hover:bg-zinc-950/30 transition-colors"
                            >
                              <td className="py-2 px-3 font-mono text-zinc-400 text-center font-medium">
                                {idx + 1}
                              </td>

                              {/* Hierarchy Level */}
                              <td className="py-2 px-3">
                                {isLocked ? (
                                  <span className="font-mono text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                                    L{sec.level || 1}
                                  </span>
                                ) : (
                                  <select
                                    value={sec.level || 1}
                                    onChange={(e) => handleSectionChange(idx, "level", parseInt(e.target.value, 10))}
                                    className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded px-1.5 py-1 text-xs text-zinc-900 dark:text-zinc-100 font-mono focus:ring-1 focus:ring-blue-500"
                                    aria-label={`Hierarchy level for section ${idx + 1}`}
                                  >
                                    <option value={1}>L1</option>
                                    <option value={2}>L2</option>
                                    <option value={3}>L3</option>
                                    <option value={4}>L4</option>
                                  </select>
                                )}
                              </td>

                              {/* Title */}
                              <td className="py-2 px-3">
                                {isLocked ? (
                                  <span className="font-medium text-zinc-900 dark:text-zinc-100">
                                    {sec.detected_title}
                                  </span>
                                ) : (
                                  <input
                                    type="text"
                                    value={sec.detected_title || ""}
                                    onChange={(e) => handleSectionChange(idx, "detected_title", e.target.value)}
                                    className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded px-2 py-1 text-xs text-zinc-900 dark:text-zinc-100 focus:ring-1 focus:ring-blue-500"
                                    aria-label={`Title for section ${idx + 1}`}
                                  />
                                )}
                              </td>

                              {/* Semantic Role */}
                              <td className="py-2 px-3">
                                {isLocked ? (
                                  <span className="font-mono text-[11px] font-medium text-blue-700 dark:text-blue-300">
                                    {sec.semantic_role || "CUSTOM_SECTION"}
                                  </span>
                                ) : (
                                  <select
                                    value={sec.semantic_role || "CUSTOM_SECTION"}
                                    onChange={(e) => handleSectionChange(idx, "semantic_role", e.target.value)}
                                    className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded px-2 py-1 text-xs text-zinc-900 dark:text-zinc-100 font-mono focus:ring-1 focus:ring-blue-500"
                                    aria-label={`Semantic role for section ${idx + 1}`}
                                  >
                                    {CANONICAL_ROLES.map((role) => (
                                      <option key={role} value={role}>
                                        {role}
                                      </option>
                                    ))}
                                  </select>
                                )}
                              </td>

                              {/* Numbering */}
                              <td className="py-2 px-3">
                                {isLocked ? (
                                  <span className="font-mono text-zinc-600 dark:text-zinc-400">
                                    {sec.numbering_pattern || "-"}
                                  </span>
                                ) : (
                                  <input
                                    type="text"
                                    value={sec.numbering_pattern || ""}
                                    placeholder="e.g. 1."
                                    onChange={(e) => handleSectionChange(idx, "numbering_pattern", e.target.value)}
                                    className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded px-2 py-1 text-xs text-zinc-900 dark:text-zinc-100 font-mono focus:ring-1 focus:ring-blue-500"
                                    aria-label={`Numbering pattern for section ${idx + 1}`}
                                  />
                                )}
                              </td>

                              {/* Confidence Display */}
                              <td className="py-2 px-3 text-center">
                                <Badge variant="outline" className={`text-[10px] py-0 px-1.5 ${confBadgeColor}`}>
                                  {confLabel}
                                </Badge>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* Warnings & Notices */}
              {reviewData?.warnings && reviewData.warnings.length > 0 && (
                <div className="bg-amber-50/70 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/60 rounded-lg p-3 text-xs text-amber-800 dark:text-amber-300 space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                    Template Analysis Notices
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-700 dark:text-amber-400">
                    {reviewData.warnings.map((w: string, i: number) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950/50">
          <Button variant="outline" size="sm" onClick={onClose} disabled={isSaving || isLocking}>
            {isLocked ? "Close" : "Cancel"}
          </Button>

          {!isLocked && (
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={handleSaveDraft}
                disabled={isSaving || isLocking}
                className="flex items-center gap-1.5"
              >
                {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Save Review Draft
              </Button>

              <Button
                size="sm"
                onClick={() => setShowLockConfirm(true)}
                disabled={isSaving || isLocking}
                className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5"
              >
                <Lock className="w-3.5 h-3.5" />
                Lock Template
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Lock Confirmation Dialog */}
      {showLockConfirm && (
        <div
          className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-zinc-950/80 backdrop-blur-sm animate-in fade-in"
          role="alertdialog"
          aria-labelledby="lock-dialog-title"
          aria-describedby="lock-dialog-desc"
        >
          <div className="w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h3 id="lock-dialog-title" className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                  Lock this template?
                </h3>
                <p className="text-xs text-zinc-500">Explicit confirmation required</p>
              </div>
            </div>

            <p id="lock-dialog-desc" className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
              After locking, this reviewed template structure will become ARM&apos;s formatting source of truth for this project.
              You will not be able to edit the review without creating a new template version.
              <br />
              <br />
              <b className="text-zinc-900 dark:text-zinc-200">The original uploaded file will remain unchanged.</b>
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowLockConfirm(false)}
                disabled={isLocking}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleConfirmLock}
                disabled={isLocking}
                className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5"
              >
                {isLocking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Lock className="w-3.5 h-3.5" />}
                Confirm & Lock
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
