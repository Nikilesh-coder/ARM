"use client";

import React, { useState, useEffect } from "react";
import { apiClient, MasterTemplateResponseDTO, TemplateFieldDTO } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import {
  FileCode2,
  Lock,
  CheckCircle2,
  Image as ImageIcon,
  Type,
  AlignLeft,
  ListFilter,
  Table as TableIcon,
  Layers,
  ChevronDown,
  ChevronUp,
  Sparkles,
  ShieldCheck,
  Building,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export function MasterTemplateCard() {
  const [masterTemplate, setMasterTemplate] = useState<MasterTemplateResponseDTO | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedFilter, setSelectedFilter] = useState<string>("all");
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    fetchMasterTemplate();
  }, []);

  const fetchMasterTemplate = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getMasterTemplate();
      if (data) {
        setMasterTemplate(data);
      }
    } catch {
      // Fallback display if offline
    } finally {
      setIsLoading(false);
    }
  };

  const fields = masterTemplate?.fields || [];
  const filteredFields = fields.filter((f) => {
    if (selectedFilter === "all") return true;
    return f.field_type === selectedFilter;
  });

  const getFieldTypeBadge = (type: string) => {
    switch (type) {
      case "text":
        return <Badge variant="outline" className="text-[10px] text-blue-500 border-blue-500/30">Text</Badge>;
      case "long_text":
        return <Badge variant="outline" className="text-[10px] text-purple-500 border-purple-500/30">Long Text</Badge>;
      case "image":
        return <Badge variant="outline" className="text-[10px] text-amber-500 border-amber-500/30">Image Slot</Badge>;
      case "list":
        return <Badge variant="outline" className="text-[10px] text-emerald-500 border-emerald-500/30">List</Badge>;
      case "table":
        return <Badge variant="outline" className="text-[10px] text-cyan-500 border-cyan-500/30">Table</Badge>;
      default:
        return <Badge variant="outline" className="text-[10px] text-zinc-400">{type}</Badge>;
    }
  };

  return (
    <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-6 shadow-sm space-y-5 transition-colors duration-300">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-zinc-200 dark:border-zinc-850">
        <div className="flex items-start gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base sm:text-lg font-semibold tracking-tight text-zinc-900 dark:text-white">
                Fixed College Master Template
              </h2>
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-[10px] font-mono font-medium flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> Locked Specification
              </span>
              <span className="px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-600 dark:text-blue-400 text-[10px] font-mono font-medium">
                Configured Once • Reusable
              </span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-2xl leading-relaxed">
              The official standard report template for engineering submissions. Typography, margins, headers, and footers remain intact. ARM automatically populates all 20 replacement fields for each project.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
          <a
            href={`${API_BASE_URL}/api/v1/templates/00000000-0000-0000-0000-000000000001/raw-download`}
            target="_blank"
            rel="noopener noreferrer"
            download
            className="text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors cursor-pointer shadow-xs"
            title="Download the exact raw Master Template file"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Original Template</span>
          </a>
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 transition-colors cursor-pointer"
          >
            <span>{isExpanded ? "Hide Fields" : "Inspect 20 Template Fields"}</span>
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Highlights Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 rounded-xl border border-zinc-200 dark:border-zinc-850 bg-zinc-50/70 dark:bg-zinc-900/50">
          <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider block">Fields Defined</span>
          <span className="text-sm sm:text-base font-bold text-zinc-900 dark:text-white mt-0.5 block">20 Reusable Slots</span>
        </div>
        <div className="p-3 rounded-xl border border-zinc-200 dark:border-zinc-850 bg-zinc-50/70 dark:bg-zinc-900/50">
          <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider block">Cover & Info</span>
          <span className="text-sm sm:text-base font-bold text-blue-600 dark:text-blue-400 mt-0.5 block">5 Title/Guide Fields</span>
        </div>
        <div className="p-3 rounded-xl border border-zinc-200 dark:border-zinc-850 bg-zinc-50/70 dark:bg-zinc-900/50">
          <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider block">Section Chapters</span>
          <span className="text-sm sm:text-base font-bold text-purple-600 dark:text-purple-400 mt-0.5 block">12 Chapters & Lists</span>
        </div>
        <div className="p-3 rounded-xl border border-zinc-200 dark:border-zinc-850 bg-zinc-50/70 dark:bg-zinc-900/50">
          <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider block">Figures / Images</span>
          <span className="text-sm sm:text-base font-bold text-amber-600 dark:text-amber-400 mt-0.5 block">3 Dedicated Slots</span>
        </div>
      </div>

      {/* Expandable Field Inspector */}
      {isExpanded && (
        <div className="pt-3 border-t border-zinc-200 dark:border-zinc-850 space-y-4 animate-in fade-in duration-200">
          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 flex-wrap text-xs">
            <span className="text-[11px] text-zinc-500 mr-1">Filter Type:</span>
            {[
              { id: "all", label: "All (20)" },
              { id: "text", label: "Text (5)" },
              { id: "long_text", label: "Long Text (7)" },
              { id: "list", label: "Lists (5)" },
              { id: "image", label: "Images (3)" },
            ].map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setSelectedFilter(f.id)}
                className={cn(
                  "px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors cursor-pointer",
                  selectedFilter === f.id
                    ? "bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-semibold"
                    : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900"
                )}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Table of Fields */}
          <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/80 text-[11px] font-medium text-zinc-500 uppercase tracking-wider">
                  <th className="py-2.5 px-3">#</th>
                  <th className="py-2.5 px-3">Field Name</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Section / Page</th>
                  <th className="py-2.5 px-3">Placeholder Identifier</th>
                  <th className="py-2.5 px-3">Content / Dimension Limits</th>
                  <th className="py-2.5 px-3 text-right">Requirement</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-850">
                {filteredFields.map((field, idx) => (
                  <tr
                    key={field.field_name || idx}
                    className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/30 transition-colors"
                  >
                    <td className="py-2.5 px-3 font-mono text-[11px] text-zinc-400">
                      {field.ordering || idx + 1}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-zinc-900 dark:text-white">
                      <div className="flex flex-col">
                        <span>{field.field_label || field.field_name}</span>
                        <span className="font-mono text-[10px] text-zinc-400">{field.field_name}</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      {getFieldTypeBadge(field.field_type)}
                    </td>
                    <td className="py-2.5 px-3 text-zinc-600 dark:text-zinc-300">
                      {field.page_or_section || field.section_key || "Cover"}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-blue-600 dark:text-blue-400">
                      {field.placeholder_identifier || `{{${field.field_name.toUpperCase()}}}`}
                    </td>
                    <td className="py-2.5 px-3 text-[11px] text-zinc-500">
                      {field.field_type === "image" && field.image_dimensions?.width ? (
                        <span>{field.image_dimensions.width}×{field.image_dimensions.height} ({field.image_dimensions.aspect_ratio || "16:9"})</span>
                      ) : field.content_limits?.min_words ? (
                        <span>{field.content_limits.min_words}–{field.content_limits.max_words} words</span>
                      ) : field.content_limits?.min_items ? (
                        <span>{field.content_limits.min_items}–{field.content_limits.max_items} items</span>
                      ) : (
                        <span className="text-zinc-400">—</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {field.is_required ? (
                        <span className="text-[10px] font-semibold text-red-500 dark:text-red-400">Required</span>
                      ) : (
                        <span className="text-[10px] text-zinc-400">Optional</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
