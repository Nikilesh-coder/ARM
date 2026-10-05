import React from "react";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { GetStartedSection } from "@/components/arm/get-started-section";
import { Badge } from "@/components/ui/badge";
import {
  FolderGit2,
  FileCode2,
  Database,
  Cpu,
  FileCheck2,
  Download,
} from "lucide-react";

export default function HowItWorksPage() {
  const workflow = [
    {
      step: "01",
      icon: FolderGit2,
      title: "Initialize Your Project",
      subtitle: "Define Topic, Department, and Guide",
      description:
        "Create an academic project record. Select your document type—B.Tech Capstone Report, M.Tech Thesis, Seminar Survey, or Internship Diary.",
    },
    {
      step: "02",
      icon: FileCode2,
      title: "Upload College Template",
      subtitle: "Deterministic XML Style Learning",
      description:
        "Provide your college's sample Word document (.docx). ARM's template engine parses paragraph styles, font names, heading points, margins (e.g. 1.25 in left for spiral/hard binding), and header/footer configurations.",
    },
    {
      step: "03",
      icon: Database,
      title: "Deposit Project Evidence",
      subtitle: "Grounding in Real Artifacts",
      description:
        "Upload code snippets, database schemas, screenshots, test results, and literature references. ARM links each chapter to these genuine artifacts, ensuring no fake numbers or hallucinated claims.",
    },
    {
      step: "04",
      icon: Cpu,
      title: "ARM Synthesizes Content",
      subtitle: "Structured Chapter Generation",
      description:
        "Using your evidence and project scope, ARM drafts comprehensive academic prose, formulates equations, and arranges citations according to IEEE or APA conventions.",
    },
    {
      step: "05",
      icon: FileCheck2,
      title: "Deterministic Compilation",
      subtitle: "Native python-docx Assembly",
      description:
        "ARM compiles the content into your college's exact layout using native OpenXML routines. Headings, margins, table borders, and Roman/Arabic page numbering are applied deterministically.",
    },
    {
      step: "06",
      icon: Download,
      title: "Preview & Download",
      subtitle: "Full Inspection Control",
      description:
        "Review the generated report section-by-section in the Document Preview console, check citation integrity, and export production-ready .docx and .pdf files.",
    },
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 flex flex-col transition-colors duration-300">
      <PublicNav />

      <main className="flex-1 max-w-5xl mx-auto px-6 py-20 w-full">
        <div className="text-center max-w-3xl mx-auto mb-20">
          <Badge variant="accent" className="mb-4">
            Synthesis Workflow
          </Badge>
          <h1 className="text-3xl sm:text-5xl font-light text-zinc-900 dark:text-white tracking-tight mb-4">
            How ARM Works
          </h1>
          <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 leading-relaxed">
            A transparent, six-step engineering workflow ensuring institutional compliance without manual document formatting headaches.
          </p>
        </div>

        <div className="space-y-8 relative">
          {workflow.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={item.step}
                className="flex flex-col md:flex-row items-start gap-6 p-6 sm:p-8 rounded-2xl border border-zinc-800 bg-zinc-950/70 hover:border-zinc-700 transition-all"
              >
                <div className="flex items-center gap-4 shrink-0">
                  <span className="font-mono text-2xl font-bold text-zinc-600">
                    {item.step}
                  </span>
                  <div className="w-12 h-12 rounded-xl bg-zinc-900 border border-zinc-750 flex items-center justify-center text-blue-400">
                    <Icon className="w-6 h-6" />
                  </div>
                </div>

                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <h3 className="text-lg font-semibold text-white tracking-tight">
                      {item.title}
                    </h3>
                    <span className="text-xs font-mono text-zinc-500">• {item.subtitle}</span>
                  </div>
                  <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed mt-2">
                    {item.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </main>

      <GetStartedSection />
      <PublicFooter />
    </div>
  );
}
