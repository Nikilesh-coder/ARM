"use client";

import React from "react";
import Link from "next/link";
import {
  BarChart3,
  Cpu,
  HardDrive,
  FileCheck2,
  CheckCircle2,
  ArrowUpRight,
  ShieldCheck,
  Zap
} from "lucide-react";
import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";

export default function UsagePage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <AppHeader />

      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <AppSidebar />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">Usage &amp; Academic Quotas</h1>
              <p className="text-xs text-slate-500 mt-1">
                Monitor your project compilation compute, storage volume, and AI token metering.
              </p>
            </div>
            <Link href="/pricing">
              <Button variant="outline" size="sm">
                View Academic Tiers <ArrowUpRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </Link>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {/* Storage Quota */}
            <Card>
              <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <CardTitle className="text-sm">Storage Volume</CardTitle>
                <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                  <HardDrive className="w-4 h-4" />
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-baseline justify-between text-xs">
                  <span className="text-2xl font-black text-slate-900">14.2 MB</span>
                  <span className="text-slate-400 font-semibold">of 500 MB</span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div className="bg-blue-600 h-full rounded-full" style={{ width: "3%" }} />
                </div>
                <p className="text-[11px] text-slate-500">
                  Includes 7 evidence diagrams, database schemas, and 3 compiled DOCX revisions.
                </p>
              </CardContent>
            </Card>

            {/* AI Generation Tokens */}
            <Card>
              <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <CardTitle className="text-sm">AI Synthesis Compute</CardTitle>
                <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <Cpu className="w-4 h-4" />
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-baseline justify-between text-xs">
                  <span className="text-2xl font-black text-slate-900">48,200</span>
                  <span className="text-slate-400 font-semibold">of 250,000 Tokens</span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div className="bg-indigo-600 h-full rounded-full" style={{ width: "19%" }} />
                </div>
                <p className="text-[11px] text-slate-500">
                  Used by Gemini 2.5 Flash for section-by-section draft generation.
                </p>
              </CardContent>
            </Card>

            {/* Compilation Jobs */}
            <Card>
              <CardHeader className="pb-3 flex flex-row items-center justify-between">
                <CardTitle className="text-sm">Deterministic DOCX Compiles</CardTitle>
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <FileCheck2 className="w-4 h-4" />
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-baseline justify-between text-xs">
                  <span className="text-2xl font-black text-slate-900">12</span>
                  <span className="text-slate-400 font-semibold">of Unlimited</span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div className="bg-emerald-600 h-full rounded-full" style={{ width: "100%" }} />
                </div>
                <p className="text-[11px] text-slate-500">
                  High-speed OpenXML AST compilation runs locally on server instances.
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Job Activity Ledger */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Recent Compute &amp; Compilation Jobs</CardTitle>
              <CardDescription>Real-time audit log of asynchronous synthesis operations</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-y border-slate-100 text-slate-500 uppercase font-semibold text-[10px] tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Job ID</th>
                      <th className="py-3 px-4">Operation Type</th>
                      <th className="py-3 px-4">Target Artifact</th>
                      <th className="py-3 px-4">Duration</th>
                      <th className="py-3 px-4 text-right">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {[
                      { id: "job_comp_0821", op: "document_compilation", target: "VTU_BTech_Final_v1.2.docx", duration: "1.4s", status: "completed" },
                      { id: "job_ast_0819", op: "template_analysis", target: "VTU_Standard_2026.docx", duration: "0.8s", status: "completed" },
                      { id: "job_ai_0814", op: "section_generation", target: "Chapter 3: System Architecture", duration: "3.2s", status: "completed" },
                      { id: "job_ai_0809", op: "section_generation", target: "Chapter 2: Literature Survey", duration: "2.9s", status: "completed" },
                    ].map((row) => (
                      <tr key={row.id} className="hover:bg-slate-50/50">
                        <td className="py-3.5 px-4 font-mono text-slate-700">{row.id}</td>
                        <td className="py-3.5 px-4 capitalize font-semibold text-slate-800">{row.op.replace("_", " ")}</td>
                        <td className="py-3.5 px-4 text-blue-700 font-medium">{row.target}</td>
                        <td className="py-3.5 px-4 text-slate-500 font-mono text-[11px]">{row.duration}</td>
                        <td className="py-3.5 px-4 text-right">
                          <Badge variant="success">Completed</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </main>
      </div>
    </div>
  );
}
