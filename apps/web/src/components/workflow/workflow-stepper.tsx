import React from "react";
import Link from "next/link";
import { FolderPlus, FileUp, Database, FileCheck2, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface WorkflowStepperProps {
  currentStep?: 1 | 2 | 3 | 4;
  className?: string;
}

const STEPS = [
  { step: 1, label: "Create Project", href: "/projects", icon: FolderPlus, desc: "Academic scope & metadata" },
  { step: 2, label: "Upload Template", href: "/templates", icon: FileUp, desc: "Institutional DOCX geometry" },
  { step: 3, label: "Add Evidence", href: "/evidence", icon: Database, desc: "Screenshots, code, benchmarks" },
  { step: 4, label: "Generate Report", href: "/reports", icon: FileCheck2, desc: "Deterministic DOCX synthesis" },
];

export function WorkflowStepper({ currentStep = 1, className }: WorkflowStepperProps) {
  return (
    <div className={cn("bg-white border border-slate-200/80 rounded-2xl p-4 sm:p-5 shadow-xs mb-8", className)}>
      <div className="flex items-center justify-between mb-3 px-1">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Core Academic Workflow
        </span>
        <span className="text-xs text-blue-600 font-semibold">
          Step {currentStep} of 4
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {STEPS.map((item) => {
          const isDone = item.step < currentStep;
          const isCurrent = item.step === currentStep;
          const Icon = item.icon;

          return (
            <Link
              key={item.step}
              href={item.href}
              className={cn(
                "group relative p-3.5 rounded-xl border transition flex items-start space-x-3",
                isCurrent
                  ? "bg-blue-50/70 border-blue-400 ring-2 ring-blue-500/20"
                  : isDone
                  ? "bg-emerald-50/40 border-emerald-300 hover:bg-emerald-50/80"
                  : "bg-slate-50/70 border-slate-200 hover:bg-slate-100/70 opacity-80"
              )}
            >
              <div
                className={cn(
                  "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold",
                  isCurrent
                    ? "bg-blue-600 text-white shadow-xs"
                    : isDone
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-200 text-slate-700"
                )}
              >
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-1.5">
                  <span
                    className={cn(
                      "text-xs font-bold truncate",
                      isCurrent
                        ? "text-blue-900"
                        : isDone
                        ? "text-emerald-950"
                        : "text-slate-700"
                    )}
                  >
                    {item.step}. {item.label}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 truncate mt-0.5">{item.desc}</p>
              </div>
              {item.step < 4 && (
                <ArrowRight className="hidden lg:block absolute -right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 z-10" />
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
