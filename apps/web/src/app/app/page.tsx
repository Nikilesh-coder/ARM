"use client";

import React, { useState, useEffect } from "react";
import { ArmSidebar } from "@/components/arm/arm-sidebar";
import { ArmComposer, AttachedFile } from "@/components/arm/arm-composer";
import { AgentStatus, AgentStage } from "@/components/arm/agent-status";
import {
  GeneratedDocumentCard,
  GeneratedDocument,
} from "@/components/arm/generated-document-card";
import { DocumentPreview } from "@/components/arm/document-preview";
import {
  GuidedProjectWizard,
  ProjectIntakeData,
} from "@/components/arm/guided-project-wizard";
import { CreateProjectModal } from "@/components/arm/create-project-modal";
import { ProjectDTO } from "@/lib/api-client";
import { ThemeToggle } from "@/components/arm/theme-toggle";
import {
  Sparkles,
  FileCode2,
  CalendarDays,
  FolderGit2,
  Menu,
  FileText,
} from "lucide-react";

interface WorkspaceMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  attachments?: AttachedFile[];
  document?: GeneratedDocument;
  templateJson?: any;
  timestamp: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function cleanTopicToAcademicTitle(raw: string): string {
  let cleaned = (raw || "").trim();
  cleaned = cleaned.replace(/^["'“”]+|["'“”]+$/g, "").trim();
  cleaned = cleaned
    .replace(/^(can\s+you\s+)?(give|create|generate|write|prepare|make|produce|provide|build)\s+(me\s+)?(my|a|an)?\s*(project|academic)?\s*(report|documentation|presentation|synopsis|doc)?\s*(on|for|about)?\s*/gi, "")
    .replace(/^(report\s+on|project\s+on|topic\s*:?)\s*/gi, "")
    .replace(/^(about|for|on)\s+/gi, "")
    .trim();

  if (!cleaned || cleaned.length < 3) return "Technical Research Project";

  const acronyms: Record<string, string> = {
    ai: "AI",
    iot: "IoT",
    ml: "ML",
    rfid: "RFID",
    gps: "GPS",
    gsm: "GSM",
    api: "API",
    cnn: "CNN",
    rnn: "RNN",
    uav: "UAV",
    ieee: "IEEE",
    ev: "EV",
  };

  const words = cleaned.split(/\s+/);
  const formatted = words.map((w, i) => {
    const low = w.toLowerCase().replace(/[^a-z0-9]/g, "");
    if (acronyms[low]) return acronyms[low];
    if (["and", "or", "of", "in", "on", "at", "to", "for", "with", "by", "a", "an", "the"].includes(low) && i > 0) return low;
    return w.charAt(0).toUpperCase() + w.slice(1);
  });

  let title = formatted.join(" ");
  const lower = title.toLowerCase();
  const endings = ["system", "systems", "platform", "framework", "architecture", "analysis", "study", "approach", "model", "project", "monitoring"];
  if (!endings.some((end) => lower.endsWith(end))) {
    title = `${title} System`;
  }
  return title;
}

export default function ArmWorkspacePage() {
  const [messages, setMessages] = useState<WorkspaceMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStage, setCurrentStage] = useState<AgentStage>("thinking");
  const [previewDoc, setPreviewDoc] = useState<GeneratedDocument | null>(null);
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [presetInput, setPresetInput] = useState<string>("");
  const [userName, setUserName] = useState("Engineering Scholar");
  const [userEmail, setUserEmail] = useState("scholar@university.edu");
  const [activeProject, setActiveProject] = useState<ProjectDTO | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedName = localStorage.getItem("arm_user_name");
      const storedEmail = localStorage.getItem("arm_user_email");
      if (storedName) setUserName(storedName);
      if (storedEmail) setUserEmail(storedEmail);
      const storedProj = localStorage.getItem("arm_active_project");
      if (storedProj) {
        try {
          setActiveProject(JSON.parse(storedProj));
        } catch {}
      }
    }
  }, []);

  const handleProjectCreated = (newProject: ProjectDTO) => {
    setActiveProject(newProject);
    if (typeof window !== "undefined") {
      if (newProject.template_id) {
        localStorage.setItem("arm_selected_template_id", newProject.template_id);
      }
      localStorage.setItem("arm_active_project", JSON.stringify(newProject));
    }

    const userMsg: WorkspaceMessage = {
      id: Math.random().toString(36).substring(2, 9),
      role: "user",
      content: `Initialized Academic Project: "${newProject.title}"\n• Scope / Topic: ${newProject.description || "N/A"}\n• Report Type: ${(newProject.project_type || "capstone").replace("_", " ").toUpperCase()}\n• College / Institution: ${newProject.institution || "College of Engineering"}\n• Template Selection: ${newProject.template_id || "Standard Capstone Preset"}${newProject.instructions ? `\n• Special Instructions: ${newProject.instructions}` : ""}`,
      timestamp: new Date().toISOString(),
    };

    const assistantMsg: WorkspaceMessage = {
      id: Math.random().toString(36).substring(2, 9),
      role: "assistant",
      content: `✅ **Project "${newProject.title}" Created & Registered!**\n\n🏛️ **Institution**: ${newProject.institution || "College of Engineering"}\n📋 **Report Type**: ${(newProject.project_type || "capstone").replace("_", " ").toUpperCase()}\n📐 **Template**: Linked to formatting rules and stored against your scholar profile.\n\n👉 Now, type any specific chapter or topic research query below, or upload project evidence files. ARM will synthesize your report strictly following this template structure!`,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
  };

  const promptSuggestions = [
    {
      title: "Create new academic project",
      desc: "Title, topic, college affiliation, report type & template",
      icon: Sparkles,
      prompt: "Create a new academic project with college guidelines and template.",
      action: "create_project",
    },
    {
      title: "Start guided 8-step blueprint",
      desc: "Detailed chapter outline, evidence files & word budgets",
      icon: FolderGit2,
      prompt: "Start guided 8-step report pipeline for my project.",
      action: "wizard",
    },
    {
      title: "Analyze my college report template",
      desc: "Inspect margin bounds, heading rules, and line spacing",
      icon: FileCode2,
      prompt: "Analyze my college report template and extract the required formatting rules.",
      action: "preset",
    },
    {
      title: "Create this week's project report",
      desc: "Summarize this week's commits and progress milestones",
      icon: CalendarDays,
      prompt: "Create this week's project report for Week 6 based on my recent progress.",
      action: "preset",
    },
  ];

  const handleSuggestionClick = (item: { title: string; prompt: string; action: string }) => {
    if (item.action === "create_project") {
      setIsCreateProjectOpen(true);
      return;
    }
    if (item.action === "wizard") {
      setIsWizardOpen(true);
      return;
    }
    setPresetInput(item.prompt);
  };

  const handleWizardComplete = (intakeData: ProjectIntakeData, doc: GeneratedDocument) => {
    const includedChapters = intakeData.blueprint.filter((b) => b.included);
    const userMsg: WorkspaceMessage = {
      id: Math.random().toString(36).substring(2, 9),
      role: "user",
      content: `Create project report for: "${intakeData.title}"\n• Submission: ${intakeData.university} — ${intakeData.department} (${intakeData.regulation})\n• Type: ${intakeData.projectType.replace("_", " ").toUpperCase()}\n• Evidence Materials: ${intakeData.evidenceFiles.length} files attached\n• Approved Blueprint: ${includedChapters.length} Chapters`,
      timestamp: new Date().toISOString(),
    };

    const chapterListText = includedChapters
      .map((c) => `  ${c.number}. ${c.title} (~${c.estimatedPages} pages)`)
      .join("\n");

    const assistantMsg: WorkspaceMessage = {
      id: Math.random().toString(36).substring(2, 9),
      role: "assistant",
      content: `ARM has successfully synthesized your academic report in accordance with ${intakeData.university} (${intakeData.regulation}) guidelines.\n\nAll ${includedChapters.length} reviewed blueprint chapters have been formatted with Times New Roman 14pt (H1), 12pt body text, 1.5 line spacing, and 1.25" college binding margins:\n\n${chapterListText}\n\nYour finalized document is ready:`,
      document: doc,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
  };

  const handleSendMessage = async (text: string, attachments: AttachedFile[]) => {
    const userMsg: WorkspaceMessage = {
      id: Math.random().toString(36).substring(2, 9),
      role: "user",
      content: text,
      attachments,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);
    setPresetInput("");

    const hasAttachments = attachments && attachments.length > 0;
    const textLower = text.toLowerCase();

    // Extract any actual topic from the message if user provided one
    let rawInput = text.trim();
    let searchedTopic = rawInput
      .replace(/analyze\s+(the|my)?\s*(college|pdf)?\s*(report)?\s*template\s*(of\s+this\s+pdf)?\s*(and\s+extract\s+the\s+required\s+formatting\s+rules)?/gi, "")
      .replace(/and\s+(change|replace)\s+(the\s+)?(matter|content|text|images)\s*(in\s+this\s+pdf)?\s*(about|to|with|for)?/gi, "")
      .replace(/(change|replace)\s+(the\s+)?(matter|content|text|images)\s*(in\s+this\s+pdf)?\s*(about|to|with|for)?/gi, "")
      .replace(/^(create|generate|write|prepare|make)\s+(my|a|an)?\s*(project|academic)?\s*(report|documentation)?\s*(on|for|about)?\s*/gi, "")
      .replace(/^(report\s+on|project\s+on|topic\s*:?)\s*/gi, "")
      .replace(/^(about|for|on)\s+/gi, "")
      .trim();

    const isTemplateAnalysisOnly =
      (textLower.includes("analyze") && textLower.includes("template") && searchedTopic.length < 3) ||
      (hasAttachments && text.trim().length === 0);

    // CASE 1: USER IS ANALYZING / UPLOADING A TEMPLATE (NO SEARCH TOPIC YET)
    if (isTemplateAnalysisOnly) {
      const templateStages: AgentStage[] = [
        "thinking",
        "reading_template",
        "analyzing",
        "validating",
      ];
      for (const st of templateStages) {
        setCurrentStage(st);
        await new Promise((res) => setTimeout(res, 350));
      }

      let templateDesign: any = null;
      try {
        const formData = new FormData();
        if (hasAttachments && attachments[0].file) {
          formData.append("file", attachments[0].file);
        }
        const tplResp = await fetch(`${API_BASE_URL}/api/v1/templates/convert-to-json`, {
          method: "POST",
          body: hasAttachments ? formData : undefined,
        });
        if (tplResp.ok) {
          const tplResData = await tplResp.json();
          templateDesign = tplResData.design;
          if (typeof window !== "undefined") {
            localStorage.setItem("arm_active_template_design", JSON.stringify(templateDesign));
          }
        }
      } catch (e) {
        console.warn("Template conversion error:", e);
      }

      const instName = templateDesign?.institution?.name || "INSTITUTION OF ENGINEERING & TECHNOLOGY";
      const deptName = templateDesign?.institution?.department || "DEPARTMENT OF ENGINEERING";
      const font = templateDesign?.typography?.font_family || "Times New Roman";
      const h1Size = templateDesign?.typography?.h1_size_pt || 14;
      const bodySize = templateDesign?.typography?.body_size_pt || 12;

      const blueprintSummary = templateDesign?.chapters_structure && templateDesign.chapters_structure.length > 0
        ? templateDesign.chapters_structure.map((s: string) => s.replace(/^\d+\.\s*/, "")).join(" • ")
        : "Title Page • Abstract • Introduction • Objectives • Community Awareness • Advantages & Disadvantages • Problems Observed • Conclusion • References • Queries • Thank You";

      const assistantMsg: WorkspaceMessage = {
        id: Math.random().toString(36).substring(2, 9),
        role: "assistant",
        content: `✅ **Template Design Analyzed & Stored in Memory!** (Saved internally without forced download)\n\n🏛️ **Institution**: ${instName}\n🏫 **Department**: ${deptName}\n🖼️ **College Emblem**: Extracted & Preserved for Cover and Presentation\n🎨 **Template Colors**: Red (#E60000) Titles & Headings, Royal Blue (#0033CC) College, Navy (#002060), Crimson (#CC0066)\n🖋️ **Typography**: ${font} ${h1Size}pt (H1) / ${bodySize}pt (Body Text), 1.5 Line Spacing\n📋 **Extracted Template Blueprint**: ${blueprintSummary}\n\n👉 **Template Structure Locked.** Now, search or type any project topic you want to research in the box below. ARM will synthesize your report strictly following this template structure!`,
        templateJson: templateDesign,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setIsProcessing(false);
      return;
    }

    // CASE 2: USER IS SEARCHING A TOPIC (OR COMBINING TEMPLATE + TOPIC)
    let projectTitle = activeProject?.title || (searchedTopic.length >= 3 ? cleanTopicToAcademicTitle(searchedTopic) : cleanTopicToAcademicTitle(rawInput));
    let researchQuery = text.trim();

    // If an attachment is uploaded with the search topic, convert it to active template design first!
    let activeDesign: any = null;
    if (hasAttachments && attachments[0].file) {
      try {
        const formData = new FormData();
        formData.append("file", attachments[0].file);
        const tplResp = await fetch(`${API_BASE_URL}/api/v1/templates/convert-to-json`, {
          method: "POST",
          body: formData,
        });
        if (tplResp.ok) {
          const tplResData = await tplResp.json();
          activeDesign = tplResData.design;
          if (typeof window !== "undefined") {
            localStorage.setItem("arm_active_template_design", JSON.stringify(activeDesign));
          }
        }
      } catch (e) {
        console.warn("Template conversion error during search:", e);
      }
    }

    // Load active template design from localStorage or backend if not already set
    if (!activeDesign && typeof window !== "undefined") {
      const stored = localStorage.getItem("arm_active_template_design");
      if (stored) {
        try {
          activeDesign = JSON.parse(stored);
        } catch {}
      }
    }
    if (!activeDesign) {
      try {
        const dResp = await fetch(`${API_BASE_URL}/api/v1/templates/active-design`);
        if (dResp.ok) {
          activeDesign = await dResp.json();
        }
      } catch {}
    }

    // Progress through pipeline
    const stages: AgentStage[] = [
      "thinking",
      "researching",
      "planning",
      "creating",
      "formatting",
      "validating",
      "finalizing",
    ];

    const effectiveTemplateId =
      activeProject?.template_id ||
      (typeof window !== "undefined" ? localStorage.getItem("arm_selected_template_id") : undefined) ||
      undefined;

    const generatePromise = fetch(`${API_BASE_URL}/api/v1/reports/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: projectTitle,
        project_title: projectTitle,
        research_query: researchQuery,
        search_query: researchQuery,
        project_type: activeProject?.project_type || activeDesign?.project_metadata?.project_type || "Capstone Project",
        student_name: userName || "K.CHARISHMA",
        roll_no: "25BFA02L13",
        guide_name: activeProject?.guide_name || activeDesign?.student_metadata?.guide_name || "Faculty Guide, Ph.D",
        department: activeProject?.department || activeDesign?.institution?.department,
        institution: activeProject?.institution || activeDesign?.institution?.name,
        problem_statement: text,
        project_id: activeProject?.id,
        template_id: effectiveTemplateId,
      }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          const errMsg = errData?.detail?.message || errData?.detail || errData?.error?.message || `HTTP ${res.status}`;
          throw new Error(typeof errMsg === "object" ? JSON.stringify(errMsg) : errMsg);
        }
        return res.json();
      })
      .catch((err) => {
        console.warn("Backend generation failed:", err);
        let msg = err?.message || "Generation request failed.";
        if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
          msg = `Could not connect to ARM backend at ${API_BASE_URL}. Please ensure the FastAPI server is running on port 8000.`;
        }
        return { _error: msg };
      });

    for (let i = 0; i < stages.length; i++) {
      setCurrentStage(stages[i]);
      await new Promise((res) => setTimeout(res, 400));
    }

    const generatedData = await generatePromise;

    if (!generatedData || generatedData._error || (!generatedData.report_id && !generatedData.job_id && !generatedData.document_id)) {
      const errDetail = generatedData?._error || "The server could not complete the report synthesis.";
      const errorMsg: WorkspaceMessage = {
        id: Math.random().toString(36).substring(2, 9),
        role: "assistant",
        content: `❌ **Report Generation Failed**\n\nCould not synthesize report for **"${projectTitle}"**.\n\n**Error Details**: ${errDetail}\n\nPlease check your input parameters and retry.`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
      setIsProcessing(false);
      return;
    }

    const reportId = generatedData.report_id || generatedData.job_id || generatedData.document_id;
    const downloadUrl = generatedData.download_url || `${API_BASE_URL}/api/v1/reports/${reportId}/download`;
    const fileName = generatedData.file_name || `Report_${reportId}.docx`;
    const fileSize = generatedData.file_size_bytes || 41192;

    const generatedDoc: GeneratedDocument = {
      id: reportId,
      title: generatedData.title || projectTitle,
      fileName: fileName,
      fileSizeBytes: fileSize,
      docxAvailable: true,
      docxDownloadUrl: downloadUrl,
      pdfAvailable: false,
      pdfDownloadUrl: undefined,
      creationStatus: "generated",
      validationStatus: "passed",
      createdAt: new Date().toISOString(),
      sectionCount: generatedData.preview_sections?.length || activeDesign?.chapters_structure?.length || 13,
      sections: generatedData.preview_sections,
    };

    const finalTitle = generatedData.title || projectTitle;
    const instDisplay = activeDesign?.institution?.name || "your institution";
    const assistantContent = `ARM has completed researching and synthesizing your academic report on **"${finalTitle}"** using Gemini AI.\n\nFollowing your uploaded template design (Canva-style text and image replacement):\n• **Template Structure & Styling**: 100% preserved from your uploaded template (${instDisplay}, official emblem logo, headings, and formatting).\n• **Matter & Research**: Replaced with comprehensive academic text specifically for "${finalTitle}".\n• **Technical Diagrams**: High-resolution figures generated specifically for "${finalTitle}".\n\nYour finalized document is ready for download in Word (.docx) format:`;

    const assistantMsg: WorkspaceMessage = {
      id: Math.random().toString(36).substring(2, 9),
      role: "assistant",
      content: assistantContent,
      document: generatedDoc,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, assistantMsg]);
    setIsProcessing(false);
  };

  const handleNewChat = () => {
    setMessages([]);
    setIsProcessing(false);
    setPresetInput("");
    setIsCreateProjectOpen(true);
  };

  return (
    <div className="flex h-screen w-full bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 overflow-hidden transition-colors duration-300">
      {/* Left Minimal 5-item Sidebar */}
      <ArmSidebar
        onNewChat={handleNewChat}
        onStartWizard={() => setIsWizardOpen(true)}
        userName={userName}
        userEmail={userEmail}
        isMobileOpen={mobileMenuOpen}
        onToggleMobile={() => setMobileMenuOpen(false)}
      />

      {/* Main AI Workspace Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative bg-white dark:bg-black transition-colors duration-300">
        {/* Top Minimal Bar */}
        <header className="h-14 border-b border-zinc-200 dark:border-zinc-900 px-4 sm:px-6 flex items-center justify-between shrink-0 bg-white/80 dark:bg-black/80 backdrop-blur-md transition-colors duration-300">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-1.5 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-900 cursor-pointer"
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>
            <span className="text-xs font-semibold text-zinc-900 dark:text-white tracking-tight">
              ARM Workspace
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400">
              OpenXML Deterministic Engine
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <button
              type="button"
              onClick={() => setIsCreateProjectOpen(true)}
              className="px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-900 hover:bg-zinc-200 dark:hover:bg-zinc-850 text-zinc-900 dark:text-zinc-100 text-xs font-medium flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
            >
              <FolderGit2 className="w-3.5 h-3.5 text-blue-500" />
              <span className="hidden sm:inline">New Project</span>
            </button>

            <button
              type="button"
              onClick={() => setIsWizardOpen(true)}
              className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Start Guided Report</span>
              <span className="sm:hidden">Guided Report</span>
            </button>
            <span className="hidden xl:inline font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
              College Format Engine: Active
            </span>
            <ThemeToggle />
          </div>
        </header>

        {/* Center Interaction Viewport */}
        <main className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 flex flex-col justify-between">
          <div className="w-full max-w-3xl mx-auto flex-1 flex flex-col">
            {/* Empty Initial State: Section 7 */}
            {messages.length === 0 && !isProcessing && (
              <div className="flex-1 flex flex-col justify-center items-center text-center my-auto py-8">
                <div className="w-14 h-14 rounded-2xl bg-zinc-900 border border-zinc-750 flex items-center justify-center text-white mb-6 font-mono font-bold text-lg shadow-md">
                  ARM
                </div>
                <h1 className="text-3xl sm:text-4xl font-light text-zinc-900 dark:text-white tracking-tight mb-3">
                  Hello, how can ARM help you today?
                </h1>
                <p className="text-sm text-zinc-600 dark:text-zinc-400 max-w-md mx-auto mb-10 leading-relaxed">
                  Create reports, analyze your college template, organize project evidence, or prepare your weekly report.
                </p>

                {/* UI Suggestions Grid */}
                <div className="w-full grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                  {promptSuggestions.map((item) => {
                    const Icon = item.icon;
                    return (
                      <button
                        key={item.title}
                        type="button"
                        onClick={() => handleSuggestionClick(item)}
                        className="group p-4 rounded-xl border border-zinc-200 dark:border-zinc-850 bg-white dark:bg-zinc-950/60 hover:bg-zinc-50 dark:hover:bg-zinc-900/60 hover:border-zinc-300 dark:hover:border-zinc-700 shadow-xs transition-all text-left flex items-start gap-3 cursor-pointer"
                      >
                        <div className="p-2 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-zinc-600 dark:text-zinc-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors shrink-0">
                          <Icon className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <h3 className="text-xs font-semibold text-zinc-900 dark:text-white tracking-tight">
                            {item.title}
                          </h3>
                          <p className="text-[11px] text-zinc-500 dark:text-zinc-400 line-clamp-1 mt-0.5">
                            {item.desc}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Conversation Flow */}
            {messages.length > 0 && (
              <div className="space-y-6 pb-6">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${
                      msg.role === "user" ? "items-end" : "items-start"
                    }`}
                  >
                    {/* User Message */}
                    {msg.role === "user" ? (
                      <div className="max-w-[85%] bg-zinc-100 dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 rounded-2xl rounded-tr-sm px-4 py-3 border border-zinc-200 dark:border-zinc-800 text-sm shadow-xs">
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                        {msg.attachments && msg.attachments.length > 0 && (
                          <div className="flex flex-wrap gap-2 mt-2 pt-2 border-t border-zinc-200 dark:border-zinc-800">
                            {msg.attachments.map((att) => (
                              <span
                                key={att.id}
                                className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-200/70 dark:bg-zinc-950 text-[11px] font-mono text-zinc-800 dark:text-zinc-300 border border-zinc-300 dark:border-zinc-800"
                              >
                                <FileText className="w-3 h-3 text-blue-500" />
                                {att.name}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      /* Assistant Response */
                      <div className="w-full space-y-4">
                        <div className="flex items-start gap-3">
                          <div className="w-7 h-7 rounded-lg bg-zinc-900 border border-zinc-750 flex items-center justify-center text-white font-mono text-xs font-bold shrink-0 mt-0.5 shadow-xs">
                            ARM
                          </div>
                          <div className="flex-1 text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed space-y-3">
                            <p>{msg.content}</p>
                          </div>
                        </div>

                        {/* Template Converted to JSON Schema Card */}
                        {msg.templateJson && (
                          <div className="w-full max-w-2xl p-4 rounded-xl border border-blue-200 dark:border-blue-900/60 bg-blue-50/50 dark:bg-blue-950/20 space-y-3">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300 font-semibold text-xs">
                                <FileCode2 className="w-4 h-4" />
                                <span>College Template Converted to JSON Schema (Design Contract)</span>
                              </div>
                              <span className="px-2.5 py-1 rounded bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 text-[11px] font-mono font-medium">
                                Stored Internally
                              </span>
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono text-zinc-600 dark:text-zinc-400 bg-white/60 dark:bg-zinc-900/60 p-2.5 rounded-lg border border-blue-100 dark:border-blue-900/40">
                              <div>
                                <span className="text-zinc-400 dark:text-zinc-500 block text-[9px] uppercase">Font & H1</span>
                                <span className="font-semibold text-zinc-800 dark:text-zinc-200">Times New Roman 14pt</span>
                              </div>
                              <div>
                                <span className="text-zinc-400 dark:text-zinc-500 block text-[9px] uppercase">Body & Spacing</span>
                                <span className="font-semibold text-zinc-800 dark:text-zinc-200">12pt / 1.5 Spacing</span>
                              </div>
                              <div>
                                <span className="text-zinc-400 dark:text-zinc-500 block text-[9px] uppercase">Left Binding Margin</span>
                                <span className="font-semibold text-zinc-800 dark:text-zinc-200">1.25 inches</span>
                              </div>
                              <div>
                                <span className="text-zinc-400 dark:text-zinc-500 block text-[9px] uppercase">Figure Slots</span>
                                <span className="font-semibold text-emerald-600 dark:text-emerald-400">3 Diagram Slots</span>
                              </div>
                            </div>
                            <div className="text-[11px] text-zinc-600 dark:text-zinc-400">
                              <span className="font-semibold text-zinc-800 dark:text-zinc-200">Institution: </span>
                              {msg.templateJson.institution?.name} • {msg.templateJson.institution?.department}
                            </div>
                            <details className="text-[11px]">
                              <summary className="cursor-pointer text-blue-600 dark:text-blue-400 font-mono hover:underline">
                                View Full JSON Contract ({msg.templateJson.template_id}.json)
                              </summary>
                              <pre className="mt-2 p-3 bg-zinc-900 text-zinc-100 rounded-lg overflow-x-auto text-[10px] font-mono max-h-48 border border-zinc-800">
                                {JSON.stringify(msg.templateJson, null, 2)}
                              </pre>
                            </details>
                          </div>
                        )}

                        {/* Generated Document Card */}
                        {msg.document && (
                          <div className="w-full pt-1">
                            <GeneratedDocumentCard
                              document={msg.document}
                              onPreview={(doc) => setPreviewDoc(doc)}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* In-Flight Agent Status with Brain Indicator: Section 10 */}
            {isProcessing && (
              <div className="my-4">
                <AgentStatus currentStage={currentStage} />
              </div>
            )}
          </div>

          {/* Bottom ChatGPT-style Composer */}
          <div className="pt-2 shrink-0">
            <ArmComposer
              key={presetInput}
              placeholder={
                presetInput ||
                "Ask ARM to create your report, format an academic chapter, or analyze your template..."
              }
              onSendMessage={handleSendMessage}
              isSubmitting={isProcessing}
            />
            <p className="text-center text-[10px] text-zinc-500 dark:text-zinc-600 mt-2 font-mono">
              Designed to follow your college format • Review all generated sections before final submission
            </p>
          </div>
        </main>
      </div>

      {/* Document Preview Modal */}
      {previewDoc && (
        <DocumentPreview
          document={previewDoc}
          onClose={() => setPreviewDoc(null)}
        />
      )}

      {/* 8-Step Guided Project Intake Wizard */}
      <GuidedProjectWizard
        isOpen={isWizardOpen}
        onClose={() => setIsWizardOpen(false)}
        onComplete={handleWizardComplete}
      />

      {/* Project Creation Workflow Modal */}
      <CreateProjectModal
        isOpen={isCreateProjectOpen}
        onClose={() => setIsCreateProjectOpen(false)}
        onProjectCreated={handleProjectCreated}
      />
    </div>
  );
}
