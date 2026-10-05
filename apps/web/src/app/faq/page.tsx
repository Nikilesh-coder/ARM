import React from "react";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { GetStartedSection } from "@/components/arm/get-started-section";
import { Badge } from "@/components/ui/badge";

export default function FAQPage() {
  const faqs = [
    {
      q: "What is ARM?",
      a: "ARM is an AI-powered academic documentation assistant designed specifically for engineering and college students. It solves the formatting struggle by combining LLM-driven content synthesis with a deterministic OpenXML formatting engine that enforces your institution's exact Word layout requirements.",
    },
    {
      q: "How does ARM create reports?",
      a: "The generation pipeline follows a strict separation of concerns: you define your project parameters, upload your college's .docx template, and attach authentic evidence (code, diagrams, datasets). ARM's AI drafts the narrative content while our deterministic document engine compiles the final file, ensuring line spacing, margins, Roman/Arabic page numbers, and headings are strictly followed.",
    },
    {
      q: "Can ARM follow my college template?",
      a: "Yes. You can upload any standard Word (.docx) guidelines document provided by your department. ARM analyzes the XML stylesheet definitions—identifying primary font faces (e.g. Times New Roman), font sizes for Title, H1, H2, body paragraphs, and explicit margin measurements.",
    },
    {
      q: "What files can I upload?",
      a: "ARM supports Word templates (.docx, .doc), academic papers and research reports (.pdf), system architecture diagrams and screenshots (.png, .jpg, .webp), benchmark tables and datasets (.csv, .json), and source code repositories (.py, .ts, .zip).",
    },
    {
      q: "Can I create weekly reports?",
      a: "Yes. ARM has a dedicated Weekly Reports module that tracks your project milestones week by week, recording hours worked, completed tasks, upcoming blockers, and faculty supervisor approval blocks.",
    },
    {
      q: "Can I download PDF and DOCX?",
      a: "Yes. Final reports are exported natively as Microsoft Word (.docx) documents so you retain full editing capabilities in desktop word processors. PDF export options are available for formal submission.",
    },
    {
      q: "Does ARM verify generated content?",
      a: "Before compilation, ARM runs structural validation checks: ensuring all mandatory sections are present, word budgets conform to guidelines, headings maintain hierarchical order, and citation references are numbered sequentially.",
    },
    {
      q: "Can I edit my report before downloading?",
      a: "Yes. The Document Preview console allows you to inspect each section, examine word counts, review citation mappings, and make adjustments before downloading the final document.",
    },
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 flex flex-col transition-colors duration-300">
      <PublicNav />

      <main className="flex-1 max-w-4xl mx-auto px-6 py-20 w-full">
        <div className="text-center mb-16">
          <Badge variant="accent" className="mb-4">
            Knowledge Base
          </Badge>
          <h1 className="text-3xl sm:text-5xl font-light text-zinc-900 dark:text-white tracking-tight mb-4">
            Frequently Asked Questions
          </h1>
          <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-xl mx-auto">
            Everything you need to know about ARM&apos;s deterministic document synthesis, template compliance, and evidence tracking.
          </p>
        </div>

        <div className="space-y-4">
          {faqs.map((faq, idx) => (
            <div
              key={idx}
              className="p-6 rounded-xl border border-zinc-800 bg-zinc-950/70 hover:border-zinc-700 transition-colors"
            >
              <h3 className="text-base font-semibold text-white mb-2 tracking-tight">
                {faq.q}
              </h3>
              <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed">
                {faq.a}
              </p>
            </div>
          ))}
        </div>
      </main>

      <GetStartedSection />
      <PublicFooter />
    </div>
  );
}
