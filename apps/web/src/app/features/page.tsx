import React from "react";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { GetStartedSection } from "@/components/arm/get-started-section";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  FileCode2,
  Database,
  Cpu,
  FileCheck2,
  CalendarDays,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";

export default function FeaturesPage() {
  const features = [
    {
      icon: FileCode2,
      title: "Template Intelligence",
      tag: "Parser Engine",
      description:
        "Upload your college's official .docx sample once. ARM reads raw OpenXML paragraph styles, font hierarchies (Times New Roman, Arial, Calibri), exact margins (1.25 in left binding), and heading numbering schemes.",
      bullets: [
        "Automatic font & size extraction",
        "Deterministic margin and gutter detection",
        "Header, footer & page number policy",
      ],
    },
    {
      icon: Database,
      title: "Evidence Locker",
      tag: "Academic Integrity",
      description:
        "Reports must be grounded in your authentic project work. Store source code repositories, benchmark tables, circuit diagrams, and research papers.",
      bullets: [
        "Direct code commit references",
        "Dataset and CSV metric ingestion",
        "Numbered figure and table captioning",
      ],
    },
    {
      icon: Cpu,
      title: "Structured Chapter Planner",
      tag: "AI Architecture",
      description:
        "Generate a structured chapter outline before drafting. Specify target word counts per section, mandatory institutional disclaimers, and declaration pages.",
      bullets: [
        "Chapter-by-chapter progression",
        "Word count budget controls",
        "University certificate & acknowledgement pages",
      ],
    },
    {
      icon: FileCheck2,
      title: "Native OpenXML Compilation",
      tag: "Deterministic Layout",
      description:
        "Never rely on an LLM to style your Word document. ARM's python-docx compilation engine guarantees pixel-exact margins, clean table borders, and Roman/Arabic page numbering.",
      bullets: [
        "Clean, uncorrupted .docx exports",
        "Standard IEEE / APA reference formatting",
        "Native equation rendering and syntax highlighting",
      ],
    },
    {
      icon: CalendarDays,
      title: "Weekly Project Diary",
      tag: "Continuous Tracking",
      description:
        "Maintain academic continuity across all 16 semester weeks. Track hours spent, tasks completed, upcoming milestones, and supervisor remarks.",
      bullets: [
        "Cumulative milestone tracking",
        "Faculty supervisor sign-off tables",
        "One-click semester summary compile",
      ],
    },
    {
      icon: ShieldCheck,
      title: "Plagiarism & Citation Safety",
      tag: "Verification",
      description:
        "All claims and methodology explanations are tied to cited reference literature or your genuine codebase, preventing hallucinated equations or fake citations.",
      bullets: [
        "Sequential IEEE in-text citation linking",
        "Reference list verification",
        "Zero hallucinated benchmarks",
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 flex flex-col transition-colors duration-300">
      <PublicNav />

      <main className="flex-1 max-w-6xl mx-auto px-6 py-20 w-full">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <Badge variant="accent" className="mb-4">
            Platform Capabilities
          </Badge>
          <h1 className="text-3xl sm:text-5xl font-light text-zinc-900 dark:text-white tracking-tight mb-4">
            Engineered for Academic Rigor
          </h1>
          <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 leading-relaxed">
            Discover how ARM bridges the gap between AI generation and university-compliant formatting standards.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feat) => {
            const Icon = feat.icon;
            return (
              <Card
                key={feat.title}
                className="border-zinc-800 bg-zinc-950/70 hover:border-zinc-700 transition-all flex flex-col justify-between"
              >
                <CardHeader>
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-750 flex items-center justify-center text-blue-400">
                      <Icon className="w-5 h-5" />
                    </div>
                    <Badge variant="outline" className="text-[10px]">
                      {feat.tag}
                    </Badge>
                  </div>
                  <CardTitle>{feat.title}</CardTitle>
                  <CardDescription className="leading-relaxed mt-2">
                    {feat.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="pt-4 border-t border-zinc-900 space-y-2 text-xs text-zinc-400">
                    {feat.bullets.map((b) => (
                      <div key={b} className="flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                        <span>{b}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </main>

      <GetStartedSection />
      <PublicFooter />
    </div>
  );
}
