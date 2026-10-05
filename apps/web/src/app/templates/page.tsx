"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileCode,
  Upload,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  Layers,
  ArrowRight,
  ShieldCheck,
  Eye,
  Settings2,
  FileText
} from "lucide-react";
import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { WorkflowStepper } from "@/components/workflow/workflow-stepper";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { StatusBanner } from "@/components/ui/status-banner";
import { INITIAL_MOCK_TEMPLATES, TemplateItem } from "@/lib/mock-data";

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<TemplateItem[]>(INITIAL_MOCK_TEMPLATES);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateItem>(INITIAL_MOCK_TEMPLATES[0]);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const handleSimulatedUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];

    setUploading(true);
    setUploadSuccess(false);

    setTimeout(() => {
      const newTpl: TemplateItem = {
        id: `tpl-${Date.now()}`,
        name: file.name,
        institution: "Detected University Template",
        pageSize: "A4 Portrait (210 x 297 mm)",
        margins: "Left: 31.75mm (1.25 in), Top/Bottom/Right: 25.4mm",
        defaultFont: "Times New Roman (12pt, 1.5 line spacing)",
        sectionCount: 11,
        confidenceScore: 0.97,
        status: "verified",
        updatedAt: "Just now",
      };

      setTemplates([newTpl, ...templates]);
      setSelectedTemplate(newTpl);
      setUploading(false);
      setUploadSuccess(true);
    }, 1200);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <AppHeader />

      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <AppSidebar />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">Template Intelligence Studio</h1>
              <p className="text-xs text-slate-500 mt-1">
                Upload your college format once. The OpenXML engine extracts typography, margins, and section structures.
              </p>
            </div>
            <Link href="/evidence">
              <Button variant="primary" size="sm">
                Next: Add Evidence <ArrowRight className="w-4 h-4 ml-1.5" />
              </Button>
            </Link>
          </div>

          <WorkflowStepper currentStep={2} />

          {uploadSuccess && (
            <StatusBanner
              type="success"
              title="Template Analyzed Successfully"
              message="OpenXML AST parser extracted 11 academic sections, 1.25in gutter margin, and Times New Roman 12pt rules."
              className="mb-6"
            />
          )}

          {/* Upload Zone */}
          <div className="bg-white rounded-2xl border-2 border-dashed border-slate-200 p-8 text-center mb-8 relative hover:border-blue-400 transition bg-slate-50/40">
            <input
              type="file"
              accept=".docx"
              onChange={handleSimulatedUpload}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3 shadow-xs">
              <Upload className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-800">
              {uploading ? "Analyzing DOCX OpenXML Structure..." : "Drop your college .docx template here"}
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4 leading-relaxed">
              Supports Word 2013-2026 formats (.docx). The original uploaded file will never be modified.
            </p>
            <Button variant="outline" size="sm" isLoading={uploading}>
              Browse Document (.docx)
            </Button>
          </div>

          {/* Master Templates & Detected Rules */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Template Selector List */}
            <div className="space-y-3">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400 px-1">
                Available Master Formats
              </div>
              {templates.map((tpl) => (
                <div
                  key={tpl.id}
                  onClick={() => setSelectedTemplate(tpl)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    selectedTemplate.id === tpl.id
                      ? "bg-white border-blue-500 ring-2 ring-blue-500/20 shadow-xs"
                      : "bg-white border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-bold text-slate-900 truncate">{tpl.name}</span>
                    <Badge variant={tpl.status === "verified" ? "success" : "warning"}>
                      {Math.round(tpl.confidenceScore * 100)}% Match
                    </Badge>
                  </div>
                  <p className="text-[11px] text-slate-500">{tpl.institution}</p>
                  <div className="text-[10px] text-slate-400 mt-2 flex items-center justify-between">
                    <span>{tpl.sectionCount} Sections</span>
                    <span>{tpl.updatedAt}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Selected Template Detailed Inspector */}
            <Card className="lg:col-span-2">
              <CardHeader className="flex flex-row items-start justify-between pb-3">
                <div>
                  <Badge variant="academic" className="mb-2">Normalized Template Schema v1.0</Badge>
                  <CardTitle>{selectedTemplate.name}</CardTitle>
                  <CardDescription>{selectedTemplate.institution}</CardDescription>
                </div>
                <Button variant="secondary" size="sm">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                  Locked for Synthesis
                </Button>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Physical Page Geometry */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center">
                    <Settings2 className="w-3.5 h-3.5 mr-1.5 text-blue-600" />
                    Physical Page Geometry & Margins
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                      <span className="text-slate-400 block text-[11px]">Paper Dimension</span>
                      <span className="font-semibold text-slate-800">{selectedTemplate.pageSize}</span>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                      <span className="text-slate-400 block text-[11px]">Left Binding Gutter</span>
                      <span className="font-semibold text-blue-700">31.75 mm (1.25 in)</span>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                      <span className="text-slate-400 block text-[11px]">Top / Right / Bottom</span>
                      <span className="font-semibold text-slate-800">25.4 mm (1.0 in)</span>
                    </div>
                  </div>
                </div>

                {/* Typography AST Rules */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center">
                    <FileText className="w-3.5 h-3.5 mr-1.5 text-indigo-600" />
                    Typography & Heading AST
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                      <span className="text-slate-400 block text-[11px]">Body Text Style</span>
                      <span className="font-semibold text-slate-800">{selectedTemplate.defaultFont}</span>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                      <span className="text-slate-400 block text-[11px]">Chapter Heading 1</span>
                      <span className="font-semibold text-slate-800">16pt Bold, All Caps, Centered, Page Break</span>
                    </div>
                  </div>
                </div>

                {/* Detected Academic Front & Body Matter */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center">
                    <Layers className="w-3.5 h-3.5 mr-1.5 text-purple-600" />
                    Detected Academic Section Hierarchy
                  </h4>
                  <div className="space-y-2 text-xs">
                    {[
                      { name: "Title / Cover Page", numbering: "Unnumbered (Page 1 suppressed)", mandatory: true },
                      { name: "Bonafide Certificate", numbering: "Roman lower: ii", mandatory: true },
                      { name: "Candidate Declaration", numbering: "Roman lower: iii", mandatory: true },
                      { name: "Acknowledgements", numbering: "Roman lower: iv", mandatory: true },
                      { name: "Abstract / Synopsis", numbering: "Roman lower: v", mandatory: true },
                      { name: "Table of Contents", numbering: "Roman lower: vi", mandatory: true },
                      { name: "Body Chapters (1..N)", numbering: "Arabic numerals: 1, 2, 3...", mandatory: true },
                      { name: "References & Bibliography", numbering: "Arabic numerals (Continuous)", mandatory: true },
                    ].map((sec, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-between"
                      >
                        <span className="font-semibold text-slate-800">{sec.name}</span>
                        <div className="flex items-center space-x-2">
                          <span className="text-slate-500 text-[11px]">{sec.numbering}</span>
                          <Badge variant="success">Required</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    </div>
  );
}
