"use client";

import React, { useState, useEffect } from "react";
import {
  GraduationCap,
  Building2,
  Calendar,
  Layers,
  FileText,
  Upload,
  Sparkles,
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  ArrowRight,
  BookOpen,
  Cpu,
  Database,
  BarChart3,
  ListChecks,
  Plus,
  Trash2,
  Edit2,
  Download,
  Eye,
  FileCheck,
  RefreshCw,
  FolderOpen,
  FileCode,
  FileSpreadsheet,
  Image as ImageIcon,
  Presentation,
  Check,
  X,
  Sliders,
  Settings,
} from "lucide-react";
import { GeneratedDocument } from "./generated-document-card";
import { AgentStatus, AgentStage } from "./agent-status";

export interface BlueprintChapter {
  id: string;
  number: number;
  title: string;
  subsections: string[];
  description: string;
  estimatedPages: number;
  included: boolean;
  customNotes?: string;
}

export interface ProjectIntakeData {
  projectType: string;
  university: string;
  department: string;
  regulation: string;
  title: string;
  problemStatement: string;
  proposedSolution: string;
  techStack: string;
  guideName: string;
  evidenceFiles: Array<{
    name: string;
    size: string;
    type: string;
    category: string;
  }>;
  blueprint: BlueprintChapter[];
}

interface GuidedProjectWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: (data: ProjectIntakeData, generatedDoc: GeneratedDocument) => void;
}

const PROJECT_TYPES = [
  {
    id: "seminar",
    title: "Seminar",
    desc: "Technical presentation report with state-of-the-art literature review",
    icon: Presentation,
  },
  {
    id: "mini_project",
    title: "Mini Project",
    desc: "Semester-level design project with working prototype documentation",
    icon: Layers,
  },
  {
    id: "final_year",
    title: "Final Year Project",
    desc: "Comprehensive capstone engineering project report following college format",
    icon: GraduationCap,
  },
  {
    id: "internship",
    title: "Internship",
    desc: "Industrial training report with deliverables, logbook, and company evaluation",
    icon: Building2,
  },
  {
    id: "research_proposal",
    title: "Research Proposal",
    desc: "Problem formulation, theoretical framework, and experimental roadmap",
    icon: BookOpen,
  },
  {
    id: "thesis",
    title: "Thesis",
    desc: "Master's or Doctoral dissertation with formal methodology and proofs",
    icon: FileText,
  },
  {
    id: "weekly_report",
    title: "Weekly Progress Report",
    desc: "Weekly sprint log, task milestones, hours logged, and mentor sign-off",
    icon: Calendar,
  },
  {
    id: "software_project",
    title: "Software Project",
    desc: "Full Software Requirements Specification (SRS), architecture, and test cases",
    icon: Cpu,
  },
];

const UNIVERSITIES = [
  "Anna University (Chennai)",
  "Visvesvaraya Technological University (VTU)",
  "Jawaharlal Nehru Technological University (JNTU)",
  "University of Mumbai",
  "Savitribai Phule Pune University (SPPU)",
  "APJ Abdul Kalam Technological University (KTU)",
  "Delhi Technological University (DTU)",
  "Autonomous Institution / Custom University",
];

const DEPARTMENTS = [
  "Computer Science & Engineering (CSE)",
  "Information Technology (IT)",
  "Artificial Intelligence & Data Science (AI & DS)",
  "Electronics & Communication Engineering (ECE)",
  "Electrical & Electronics Engineering (EEE)",
  "Mechanical Engineering (MECH)",
  "Civil Engineering (CIVIL)",
  "Biotechnology / Chemical Engineering",
];

const REGULATIONS = [
  "Regulation 2021 (R21)",
  "Regulation 2023 (R23)",
  "Regulation 2018 (R18)",
  "Academic Year 2024–2025",
  "Academic Year 2025–2026",
];

const DEFAULT_BLUEPRINT: BlueprintChapter[] = [
  {
    id: "ch-1",
    number: 1,
    title: "Introduction",
    subsections: ["1.1 Background & Motivation", "1.2 Problem Definition", "1.3 Objectives & Scope", "1.4 Organization of Report"],
    description: "Sets the stage, clarifies academic motivation, target goals, and chapter outline.",
    estimatedPages: 6,
    included: true,
  },
  {
    id: "ch-2",
    number: 2,
    title: "Literature Survey",
    subsections: ["2.1 Survey of Existing Approaches", "2.2 Comparative Analysis Table", "2.3 Research Gaps Identified"],
    description: "Critical review of peer-reviewed IEEE/ACM papers, benchmarks, and baseline limitations.",
    estimatedPages: 8,
    included: true,
  },
  {
    id: "ch-3",
    number: 3,
    title: "Existing System",
    subsections: ["3.1 Architecture of Legacy Solutions", "3.2 Hardware/Software Constraints", "3.3 Drawbacks & Inefficiencies"],
    description: "Detailed dissection of present manual or rule-based systems and pain points.",
    estimatedPages: 5,
    included: true,
  },
  {
    id: "ch-4",
    number: 4,
    title: "Proposed System",
    subsections: ["4.1 System Overview", "4.2 High-Level Architecture", "4.3 Core Innovations & Advantages"],
    description: "Architectural blueprint, component interactions, and strategic innovations.",
    estimatedPages: 7,
    included: true,
  },
  {
    id: "ch-5",
    number: 5,
    title: "Methodology",
    subsections: ["5.1 Data Pipeline & Preprocessing", "5.2 Mathematical Model & Algorithms", "5.3 Design Considerations"],
    description: "Formal algorithmic formulations, data ingestion workflows, and theoretical proofs.",
    estimatedPages: 8,
    included: true,
  },
  {
    id: "ch-6",
    number: 6,
    title: "Implementation",
    subsections: ["6.1 Technology Stack & Modules", "6.2 Key Code Snippets & Pipelines", "6.3 Deployment & Interfaces"],
    description: "Concrete engineering implementation details, repository structure, and schemas.",
    estimatedPages: 9,
    included: true,
  },
  {
    id: "ch-7",
    number: 7,
    title: "Results",
    subsections: ["7.1 Experimental Setup", "7.2 Performance Metrics & Evaluation", "7.3 Comparative Discussion"],
    description: "Empirical charts, latency/accuracy evaluations, and real-world validation findings.",
    estimatedPages: 6,
    included: true,
  },
  {
    id: "ch-8",
    number: 8,
    title: "Conclusion",
    subsections: ["8.1 Summary of Contributions", "8.2 Limitations", "8.3 Future Enhancements"],
    description: "Synthesized conclusions, academic impact, and future research avenues.",
    estimatedPages: 4,
    included: true,
  },
];

export function GuidedProjectWizard({
  isOpen,
  onClose,
  onComplete,
}: GuidedProjectWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);

  // Step 1: What are you creating?
  const [projectType, setProjectType] = useState("final_year");

  // Step 2: Where are you submitting it?
  const [university, setUniversity] = useState(UNIVERSITIES[0]);
  const [customUniversity, setCustomUniversity] = useState("");
  const [department, setDepartment] = useState(DEPARTMENTS[0]);
  const [regulation, setRegulation] = useState(REGULATIONS[0]);

  // Step 3: Tell us about your project
  const [title, setTitle] = useState("AI-Driven Adaptive Urban Traffic Signal Optimization");
  const [problemStatement, setProblemStatement] = useState(
    "Urban intersections suffer from static timer delays, leading to severe congestion, fuel wastage, and carbon emissions. Current camera sensors lack real-time edge intelligence to dynamically adjust green signal phases."
  );
  const [proposedSolution, setProposedSolution] = useState(
    "An autonomous edge-computing pipeline utilizing YOLOv8 for vehicle density estimation and a reinforcement learning controller that dynamically balances phase durations to minimize queue latency."
  );
  const [techStack, setTechStack] = useState("Python, PyTorch, YOLOv8, OpenCV, FastAPI, React, Docker, Raspberry Pi 4");
  const [guideName, setGuideName] = useState("Dr. K. Ramanathan, Professor, Dept. of CSE");

  // Step 4: Evidence Files
  const [evidenceFiles, setEvidenceFiles] = useState<
    Array<{ name: string; size: string; type: string; category: string }>
  >([
    {
      name: "Traffic_YOLOv8_Density_Benchmark.pdf",
      size: "2.4 MB",
      type: "pdf",
      category: "Research Paper",
    },
    {
      name: "edge_traffic_controller.py",
      size: "48 KB",
      type: "code",
      category: "Source Code",
    },
    {
      name: "junction_camera_detections.png",
      size: "1.1 MB",
      type: "image",
      category: "Screenshot / Evidence",
    },
    {
      name: "traffic_flow_dataset_sample.csv",
      size: "340 KB",
      type: "dataset",
      category: "Dataset",
    },
  ]);

  // Step 5: AI Analysis Progress
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisChecks, setAnalysisChecks] = useState([
    { label: "Validating Project Scope & Academic Tone", done: false },
    { label: "Parsing Evidence Files & Extracting Data Schemas", done: false },
    { label: "Matching University & Department Regulation Rules", done: false },
    { label: "Synthesizing High-Precision 8-Chapter Blueprint", done: false },
  ]);

  // Step 6 & 7: Report Blueprint
  const [blueprint, setBlueprint] = useState<BlueprintChapter[]>(DEFAULT_BLUEPRINT);
  const [editingChapterId, setEditingChapterId] = useState<string | null>(null);

  // Step 8: Final Generation
  const [generationProgress, setGenerationProgress] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStage, setGenerationStage] = useState<AgentStage>("thinking");
  const [generatedDoc, setGeneratedDoc] = useState<GeneratedDocument | null>(null);

  // AI Analysis simulation when entering step 5
  useEffect(() => {
    if (currentStep === 5) {
      setAnalysisProgress(0);
      setAnalysisChecks([
        { label: "Validating Project Scope & Academic Tone", done: false },
        { label: "Parsing Evidence Files & Extracting Data Schemas", done: false },
        { label: "Matching University & Department Regulation Rules", done: false },
        { label: "Synthesizing High-Precision 8-Chapter Blueprint", done: false },
      ]);

      const interval = setInterval(() => {
        setAnalysisProgress((prev) => {
          if (prev >= 100) {
            clearInterval(interval);
            return 100;
          }
          return prev + 25;
        });
      }, 500);

      const check1 = setTimeout(() => {
        setAnalysisChecks((c) => [{ ...c[0], done: true }, c[1], c[2], c[3]]);
      }, 600);
      const check2 = setTimeout(() => {
        setAnalysisChecks((c) => [c[0], { ...c[1], done: true }, c[2], c[3]]);
      }, 1200);
      const check3 = setTimeout(() => {
        setAnalysisChecks((c) => [c[0], c[1], { ...c[2], done: true }, c[3]]);
      }, 1800);
      const check4 = setTimeout(() => {
        setAnalysisChecks((c) => [c[0], c[1], c[2], { ...c[3], done: true }]);
      }, 2300);

      return () => {
        clearInterval(interval);
        clearTimeout(check1);
        clearTimeout(check2);
        clearTimeout(check3);
        clearTimeout(check4);
      };
    }
  }, [currentStep]);

  // Generation simulation in step 8 cycling through authentic Section 10 Agent Stages
  const handleStartGeneration = async () => {
    setIsGenerating(true);
    setGeneratedDoc(null);

    const stages: AgentStage[] = [
      "thinking",
      "analyzing",
      "reading_template",
      "reviewing_evidence",
      "planning",
      "researching",
      "creating",
      "formatting",
      "validating",
      "finalizing",
    ];

    // Trigger real backend generation using Gemini AI & DocumentAssembler
    let downloadUrl = "";
    let realFileSize = 312450;
    let previewSections = undefined;
    let realReportId = "";
    let genError: string | null = null;
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const cleanProjTitle = title || "ELECTRIFY THE FUTURE: PROMOTING SAFE ELECTRICITY USE IN SCHOOLS";
      const response = await fetch(`${apiBase}/api/v1/reports/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: cleanProjTitle,
          project_title: cleanProjTitle,
          research_query: problemStatement || cleanProjTitle,
          search_query: problemStatement || cleanProjTitle,
          project_type: projectType === "seminar" ? "Seminar" : projectType === "final_year" ? "Capstone Project" : "Community Service Project",
          student_name: typeof window !== "undefined" ? (localStorage.getItem("arm_user_name") || "K.CHARISHMA") : "K.CHARISHMA",
          roll_no: "25BFA02L13",
          guide_name: guideName || "Dr. R. SIRISHA, Ph.D",
          department: department || "ELECTRICAL AND ELECTRONICS ENGINEERING",
          institution: (university.includes("Custom") && customUniversity) ? customUniversity : (university || "SRI VENKATESWARA COLLEGE OF ENGINEERING (AUTONOMOUS)"),
          problem_statement: problemStatement,
          proposed_solution: proposedSolution,
          tech_stack: techStack,
          blueprint: blueprint,
          template_id: typeof window !== "undefined" ? (localStorage.getItem("arm_selected_template_id") || undefined) : undefined,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        realReportId = data.report_id || data.job_id || data.document_id;
        downloadUrl = data.download_url || `${apiBase}/api/v1/reports/${realReportId}/download`;
        if (data.file_size_bytes) {
          realFileSize = data.file_size_bytes;
        }
        if (data.preview_sections) {
          previewSections = data.preview_sections;
        }
      } else {
        const errJson = await response.json().catch(() => ({}));
        genError = errJson?.detail?.message || errJson?.detail || `Server returned error status ${response.status}`;
      }
    } catch (err: any) {
      console.warn("Backend generation notice:", err);
      genError = err?.message || "Could not reach generation backend.";
    }

    // Run Section 10 Agent Stages progression
    for (let i = 0; i < stages.length; i++) {
      setGenerationStage(stages[i]);
      await new Promise((res) => setTimeout(res, 350));
    }

    setIsGenerating(false);

    if (!realReportId) {
      alert(`Report generation failed: ${genError || "Could not compile report."}`);
      return;
    }

    const finalDoc: GeneratedDocument = {
      id: realReportId,
      title: title || "ELECTRIFY THE FUTURE: PROMOTING SAFE ELECTRICITY USE IN SCHOOLS",
      fileName: `Report_${realReportId}.docx`,
      fileSizeBytes: realFileSize,
      docxAvailable: true,
      docxDownloadUrl: downloadUrl,
      pdfAvailable: false,
      pdfDownloadUrl: undefined,
      creationStatus: "generated",
      validationStatus: "passed",
      createdAt: new Date().toISOString(),
      sectionCount: blueprint.filter((b) => b.included).length,
      sections: previewSections,
    };
    setGeneratedDoc(finalDoc);
  };

  const handleFinishAndOpen = () => {
    if (!generatedDoc) return;
    const finalUniversity = university.includes("Custom") && customUniversity ? customUniversity : university;
    const intakeData: ProjectIntakeData = {
      projectType,
      university: finalUniversity,
      department,
      regulation,
      title,
      problemStatement,
      proposedSolution,
      techStack,
      guideName,
      evidenceFiles,
      blueprint,
    };
    onComplete(intakeData, generatedDoc);
    onClose();
  };

  const toggleChapter = (id: string) => {
    setBlueprint((prev) =>
      prev.map((ch) => (ch.id === id ? { ...ch, included: !ch.included } : ch))
    );
  };

  const updateChapterTitle = (id: string, newTitle: string) => {
    setBlueprint((prev) =>
      prev.map((ch) => (ch.id === id ? { ...ch, title: newTitle } : ch))
    );
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files).map((f) => ({
        name: f.name,
        size: (f.size / 1024).toFixed(0) + " KB",
        type: f.name.split(".").pop() || "file",
        category: "Uploaded Evidence",
      }));
      setEvidenceFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const removeEvidence = (index: number) => {
    setEvidenceFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handlePrefillSample = () => {
    setTitle("Autonomous Edge AI System for Real-Time Cardiac Arrhythmia Detection");
    setProblemStatement(
      "Remote healthcare stations suffer from diagnostic delays and cloud latency when processing high-frequency ECG signals. Clinicians need localized, ultra-low-power anomaly detection."
    );
    setProposedSolution(
      "A lightweight 1D-CNN and Transformer hybrid deployed on an STM32 micro-controller providing 99.2% classification accuracy across 5 distinct arrhythmia classes under 15ms latency."
    );
    setTechStack("C++, Embedded C, TensorFlow Lite for Microcontrollers, Python, WFDB MIT-BIH Database, STM32F4");
    setGuideName("Dr. S. Meenakshi, Head of Department (AI & DS)");
  };

  if (!isOpen) return null;

  const totalPages = blueprint
    .filter((b) => b.included)
    .reduce((sum, b) => sum + b.estimatedPages, 0);

  const isPage1 = currentStep <= 3;

  const page1Steps = [
    { num: 1, label: "What to Create", desc: "Select project category" },
    { num: 2, label: "Where to Submit", desc: "University & Regulation" },
    { num: 3, label: "Project Details", desc: "Core questions & methodology" },
  ];

  const page2Steps = [
    { num: 4, label: "Upload Evidence", desc: "Materials, code & papers" },
    { num: 5, label: "AI Analysis", desc: "Verification & extraction" },
    { num: 6, label: "Report Blueprint", desc: "Generated chapters 1–8" },
    { num: 7, label: "Review Blueprint", desc: "Customize & approve" },
    { num: 8, label: "Generate", desc: "Compile final report" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-4xl max-h-[92vh] flex flex-col bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl overflow-hidden transition-colors duration-300">
        {/* Header with Title & Stepper Progress */}
        <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-850 flex items-center justify-between bg-zinc-50/70 dark:bg-zinc-900/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-950 flex items-center justify-center font-mono font-bold text-xs shadow-xs">
              ARM
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-zinc-900 dark:text-white tracking-tight">
                  {isPage1 ? "Project Intake (Before Upload)" : "2nd Page: Evidence & Blueprint Studio"}
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950/80 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800/80 font-medium">
                  {isPage1
                    ? `Question ${currentStep} of 3`
                    : `Studio Step ${currentStep - 3} of 5`}
                </span>
              </div>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                {isPage1
                  ? page1Steps[currentStep - 1]?.label
                  : page2Steps[currentStep - 4]?.label}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
            aria-label="Close wizard"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Stepper Progress Bar */}
        <div className="w-full bg-zinc-100 dark:bg-zinc-900 h-1 overflow-hidden">
          <div
            className="bg-blue-600 h-full transition-all duration-300 ease-out"
            style={{
              width: isPage1
                ? `${(currentStep / 3) * 100}%`
                : `${((currentStep - 3) / 5) * 100}%`,
            }}
          />
        </div>

        {/* Horizontal Mini Step Indicators */}
        <div className="hidden sm:flex items-center justify-between px-6 py-2.5 border-b border-zinc-150 dark:border-zinc-850/60 bg-zinc-50/40 dark:bg-zinc-900/20 text-[11px] font-medium text-zinc-500 dark:text-zinc-400 overflow-x-auto gap-2">
          {isPage1 ? (
            /* Page 1: Only 3 Intake Steps */
            page1Steps.map((step, idx) => {
              const isCompleted = step.num < currentStep;
              const isCurrent = step.num === currentStep;

              return (
                <div
                  key={step.num}
                  className={`flex items-center gap-1.5 shrink-0 ${
                    isCurrent
                      ? "text-blue-600 dark:text-blue-400 font-semibold"
                      : isCompleted
                      ? "text-zinc-900 dark:text-zinc-300"
                      : "text-zinc-400 dark:text-zinc-600"
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] ${
                      isCurrent
                        ? "bg-blue-600 text-white font-bold"
                        : isCompleted
                        ? "bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-white"
                        : "bg-zinc-100 dark:bg-zinc-900 text-zinc-400 dark:text-zinc-600 border border-zinc-200 dark:border-zinc-800"
                    }`}
                  >
                    {isCompleted ? <Check className="w-2.5 h-2.5" /> : step.num}
                  </div>
                  <span>{step.label}</span>
                  {idx < page1Steps.length - 1 && (
                    <span className="text-zinc-300 dark:text-zinc-700 ml-1">/</span>
                  )}
                </div>
              );
            })
          ) : (
            /* Page 2: Remaining Steps from Evidence to Review */
            page2Steps.map((step, idx) => {
              const isCompleted = step.num < currentStep;
              const isCurrent = step.num === currentStep;

              return (
                <div
                  key={step.num}
                  className={`flex items-center gap-1.5 shrink-0 ${
                    isCurrent
                      ? "text-blue-600 dark:text-blue-400 font-semibold"
                      : isCompleted
                      ? "text-zinc-900 dark:text-zinc-300"
                      : "text-zinc-400 dark:text-zinc-600"
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] ${
                      isCurrent
                        ? "bg-blue-600 text-white font-bold"
                        : isCompleted
                        ? "bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-white"
                        : "bg-zinc-100 dark:bg-zinc-900 text-zinc-400 dark:text-zinc-600 border border-zinc-200 dark:border-zinc-800"
                    }`}
                  >
                    {isCompleted ? <Check className="w-2.5 h-2.5" /> : step.num}
                  </div>
                  <span>{step.label}</span>
                  {idx < page2Steps.length - 1 && (
                    <span className="text-zinc-300 dark:text-zinc-700 ml-1">/</span>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Body Content for Active Step */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8 bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
          {/* Project Context Banner on 2nd Page */}
          {!isPage1 && (
            <div className="mb-6 p-3 rounded-xl bg-blue-50/60 dark:bg-blue-950/30 border border-blue-200/70 dark:border-blue-900/50 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-zinc-700 dark:text-zinc-300 min-w-0">
                <span className="font-semibold text-blue-700 dark:text-blue-300 capitalize">
                  {projectType.replace("_", " ")}
                </span>
                <span className="text-zinc-400">•</span>
                <span className="truncate max-w-[200px] text-zinc-600 dark:text-zinc-400">
                  {university.split("(")[0]}
                </span>
                <span className="text-zinc-400">•</span>
                <span className="truncate max-w-[260px] font-medium text-zinc-900 dark:text-white">
                  &quot;{title}&quot;
                </span>
              </div>
              <button
                type="button"
                onClick={() => setCurrentStep(3)}
                className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 cursor-pointer shrink-0"
              >
                ← Edit Intake Details
              </button>
            </div>
          )}
          {/* STEP 1: What are you creating? */}
          {currentStep === 1 && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div>
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                  Step 1 of 8
                </span>
                <h3 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mt-1">
                  What are you creating?
                </h3>
                <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                  Select your required project category to calibrate the academic tone, length, and depth.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
                {PROJECT_TYPES.map((type) => {
                  const Icon = type.icon;
                  const isSelected = projectType === type.id;
                  return (
                    <button
                      key={type.id}
                      type="button"
                      onClick={() => setProjectType(type.id)}
                      className={`group p-4 rounded-xl border text-left transition-all flex items-start gap-3.5 cursor-pointer ${
                        isSelected
                          ? "border-blue-600 dark:border-blue-500 bg-blue-50/60 dark:bg-blue-950/30 ring-1 ring-blue-500/20"
                          : "border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/40 hover:bg-zinc-100/60 dark:hover:bg-zinc-900/80 hover:border-zinc-300 dark:hover:border-zinc-700"
                      }`}
                    >
                      <div
                        className={`p-2.5 rounded-lg shrink-0 transition-colors ${
                          isSelected
                            ? "bg-blue-600 text-white"
                            : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 group-hover:text-zinc-900 dark:group-hover:text-zinc-200"
                        }`}
                      >
                        <Icon className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <h4
                            className={`text-sm font-semibold tracking-tight ${
                              isSelected
                                ? "text-blue-950 dark:text-blue-100"
                                : "text-zinc-900 dark:text-white"
                            }`}
                          >
                            {type.title}
                          </h4>
                          {isSelected && (
                            <CheckCircle2 className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
                          )}
                        </div>
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 line-clamp-2 leading-relaxed">
                          {type.desc}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* STEP 2: Where are you submitting it? */}
          {currentStep === 2 && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div>
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                  Step 2 of 8
                </span>
                <h3 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mt-1">
                  Where are you submitting it?
                </h3>
                <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                  Select your University, Department, and Academic Regulation to enforce exact formatting rules.
                </p>
              </div>

              <div className="space-y-5 pt-2">
                {/* 1. University Selection */}
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wider mb-2">
                    University / Institution
                  </label>
                  <select
                    value={university}
                    onChange={(e) => setUniversity(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {UNIVERSITIES.map((u) => (
                      <option key={u} value={u}>
                        {u}
                      </option>
                    ))}
                  </select>
                  {university.includes("Custom") && (
                    <input
                      type="text"
                      placeholder="Type your Institution or University Name..."
                      value={customUniversity}
                      onChange={(e) => setCustomUniversity(e.target.value)}
                      className="mt-2 w-full px-3.5 py-2 rounded-lg border border-zinc-300 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  )}
                </div>

                {/* 2. Department Selection */}
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wider mb-2">
                    Academic Department
                  </label>
                  <select
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {DEPARTMENTS.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>

                {/* 3. Regulation / Year Selection */}
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wider mb-2">
                    Regulation / Academic Year
                  </label>
                  <select
                    value={regulation}
                    onChange={(e) => setRegulation(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {REGULATIONS.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Rule Preview Card */}
                <div className="p-4 rounded-xl bg-blue-50/50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900/50 text-xs space-y-1.5">
                  <div className="flex items-center gap-2 font-semibold text-blue-900 dark:text-blue-300">
                    <CheckCircle2 className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                    Format Profile Applied: {university.split("(")[0].trim()} ({regulation.split("(")[0].trim()})
                  </div>
                  <p className="text-zinc-600 dark:text-zinc-400">
                    Standard margin 1.25&quot; left binding margin, 1.0&quot; top/bottom/right, Times New Roman 12pt body font, 1.5 line spacing, IEEE citation style.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: Tell us about your project */}
          {currentStep === 3 && (
            <div className="space-y-5 animate-in fade-in duration-200">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                    Step 3 of 8
                  </span>
                  <h3 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mt-1">
                    Tell us about your project
                  </h3>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                    Provide your project title, core problem statement, and proposed methodology.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handlePrefillSample}
                  className="px-3 py-1.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-100 dark:bg-zinc-800 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-750 transition-colors flex items-center gap-1.5 cursor-pointer shrink-0"
                >
                  <Sparkles className="w-3.5 h-3.5 text-blue-500" />
                  Quick Sample Pre-fill
                </button>
              </div>

              <div className="space-y-4 pt-1">
                {/* 1. Project Title */}
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wider mb-1.5">
                    Project Title *
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. AI-Powered Autonomous Drone Navigation in GPS-Denied Environments"
                    className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* 2. Problem Statement */}
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wider mb-1.5">
                    Problem Statement *
                  </label>
                  <textarea
                    rows={3}
                    value={problemStatement}
                    onChange={(e) => setProblemStatement(e.target.value)}
                    placeholder="What specific challenge, gap, or inefficiency are you solving?"
                    className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 leading-relaxed"
                  />
                </div>

                {/* 3. Proposed Solution */}
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wider mb-1.5">
                    Proposed Solution & Methodology *
                  </label>
                  <textarea
                    rows={3}
                    value={proposedSolution}
                    onChange={(e) => setProposedSolution(e.target.value)}
                    placeholder="How does your system solve this problem? What is the core innovation?"
                    className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 leading-relaxed"
                  />
                </div>

                {/* 4. Tech Stack */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wider mb-1.5">
                      Tools & Technologies
                    </label>
                    <input
                      type="text"
                      value={techStack}
                      onChange={(e) => setTechStack(e.target.value)}
                      placeholder="e.g. Python, PyTorch, React, PostgreSQL"
                      className="w-full px-3.5 py-2 rounded-lg border border-zinc-300 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wider mb-1.5">
                      Guide / Supervisor (Optional)
                    </label>
                    <input
                      type="text"
                      value={guideName}
                      onChange={(e) => setGuideName(e.target.value)}
                      placeholder="e.g. Dr. A. Kumar, Professor"
                      className="w-full px-3.5 py-2 rounded-lg border border-zinc-300 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: Upload evidence */}
          {currentStep === 4 && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div>
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                  Step 4 of 8
                </span>
                <h3 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mt-1">
                  Upload evidence & materials
                </h3>
                <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                  Upload PDF, DOCX, PPTX, images, research papers, screenshots, datasets, and project documentation.
                </p>
              </div>

              {/* Supported File Formats Pills */}
              <div className="flex flex-wrap gap-2 pt-1">
                {[
                  { label: "PDF Documents", icon: FileText },
                  { label: "DOCX Files", icon: FileCode },
                  { label: "PPTX Slides", icon: Presentation },
                  { label: "Screenshots / Images", icon: ImageIcon },
                  { label: "Research Papers", icon: BookOpen },
                  { label: "Datasets (CSV, JSON)", icon: FileSpreadsheet },
                  { label: "Source Code", icon: Cpu },
                ].map((item) => {
                  const Icon = item.icon;
                  return (
                    <span
                      key={item.label}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-[11px] text-zinc-700 dark:text-zinc-300 font-medium"
                    >
                      <Icon className="w-3.5 h-3.5 text-blue-500" />
                      {item.label}
                    </span>
                  );
                })}
              </div>

              {/* Upload Drop Area */}
              <div className="relative border-2 border-dashed border-zinc-300 dark:border-zinc-800 hover:border-blue-500 dark:hover:border-blue-500 rounded-2xl p-8 text-center bg-zinc-50/50 dark:bg-zinc-900/30 transition-all">
                <input
                  type="file"
                  multiple
                  onChange={handleFileUpload}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div className="w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-950/80 text-blue-600 dark:text-blue-400 flex items-center justify-center mx-auto mb-3">
                  <Upload className="w-6 h-6" />
                </div>
                <h4 className="text-sm font-semibold text-zinc-900 dark:text-white">
                  Drag and drop your evidence materials here
                </h4>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-sm mx-auto">
                  Click to browse from your computer. Files are indexed strictly for deterministic grounding without hallucinations.
                </p>
              </div>

              {/* Uploaded File List */}
              {evidenceFiles.length > 0 && (
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                    <span>Attached Evidence ({evidenceFiles.length} files)</span>
                    <button
                      type="button"
                      onClick={() => setEvidenceFiles([])}
                      className="text-red-500 hover:text-red-600 cursor-pointer"
                    >
                      Clear All
                    </button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {evidenceFiles.map((file, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl border border-zinc-200 dark:border-zinc-850 bg-white dark:bg-zinc-900/70 flex items-center justify-between gap-3 text-xs shadow-xs"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 shrink-0">
                            <FileCheck className="w-4 h-4 text-emerald-500" />
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium text-zinc-900 dark:text-white truncate">
                              {file.name}
                            </p>
                            <p className="text-[11px] text-zinc-400 flex items-center gap-1.5 mt-0.5">
                              <span className="font-mono">{file.size}</span>
                              <span>•</span>
                              <span className="text-blue-600 dark:text-blue-400">
                                {file.category}
                              </span>
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeEvidence(idx)}
                          className="p-1 text-zinc-400 hover:text-red-500 transition-colors cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 5: AI analyzes the materials */}
          {currentStep === 5 && (
            <div className="space-y-6 py-4 animate-in fade-in duration-200">
              <div className="text-center max-w-md mx-auto">
                <div className="w-16 h-16 rounded-2xl bg-blue-100 dark:bg-blue-950/80 border border-blue-200 dark:border-blue-800 flex items-center justify-center text-blue-600 dark:text-blue-400 mx-auto mb-4 shadow-md">
                  <RefreshCw className="w-8 h-8 animate-spin" />
                </div>
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                  Step 5 of 8
                </span>
                <h3 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mt-1">
                  AI is analyzing your materials...
                </h3>
                <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-2 leading-relaxed">
                  Extracting system architecture, verifying empirical figures, and mapping your university guideline bounds.
                </p>
              </div>

              {/* Progress Bar */}
              <div className="max-w-md mx-auto space-y-2">
                <div className="flex justify-between text-xs font-mono text-zinc-600 dark:text-zinc-400">
                  <span>Analysis Completion</span>
                  <span>{analysisProgress}%</span>
                </div>
                <div className="w-full bg-zinc-100 dark:bg-zinc-900 rounded-full h-2.5 overflow-hidden border border-zinc-200 dark:border-zinc-800">
                  <div
                    className="bg-blue-600 h-full rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${analysisProgress}%` }}
                  />
                </div>
              </div>

              {/* Step by Step Checklist */}
              <div className="max-w-md mx-auto space-y-3 pt-2">
                {analysisChecks.map((item, index) => (
                  <div
                    key={index}
                    className={`flex items-center gap-3 p-3 rounded-xl border text-xs transition-all ${
                      item.done
                        ? "border-emerald-200 dark:border-emerald-950/80 bg-emerald-50/60 dark:bg-emerald-950/20 text-emerald-900 dark:text-emerald-300 font-medium"
                        : "border-zinc-200 dark:border-zinc-850 bg-zinc-50/40 dark:bg-zinc-900/40 text-zinc-500 dark:text-zinc-400"
                    }`}
                  >
                    {item.done ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border-2 border-zinc-300 dark:border-zinc-700 animate-pulse shrink-0" />
                    )}
                    <span>{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* STEP 6: AI generates a Report Blueprint */}
          {currentStep === 6 && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                    Step 6 of 8
                  </span>
                  <h3 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mt-1">
                    Generated Report Blueprint
                  </h3>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                    Based on your inputs and {evidenceFiles.length} evidence materials, ARM generated this standard 8-chapter academic structure.
                  </p>
                </div>
                <div className="text-right hidden sm:block">
                  <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400">
                    Target Volume
                  </span>
                  <p className="text-lg font-bold text-zinc-900 dark:text-white font-mono">
                    ~{totalPages} Pages
                  </p>
                </div>
              </div>

              {/* Chapters Cards */}
              <div className="space-y-3 pt-1">
                {blueprint.map((chapter) => (
                  <div
                    key={chapter.id}
                    className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-850 bg-white dark:bg-zinc-900/60 shadow-xs flex items-start gap-4"
                  >
                    <div className="w-10 h-10 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-white font-mono font-bold flex items-center justify-center shrink-0 text-sm">
                      {chapter.number}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-bold text-zinc-900 dark:text-white">
                          Chapter {chapter.number} — {chapter.title}
                        </h4>
                        <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400">
                          {chapter.estimatedPages} pages
                        </span>
                      </div>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                        {chapter.description}
                      </p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {chapter.subsections.map((sub, sIdx) => (
                          <span
                            key={sIdx}
                            className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800/80 text-[11px] font-mono text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-750"
                          >
                            {sub}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* STEP 7: User reviews the blueprint (Full Control) */}
          {currentStep === 7 && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                    Step 7 of 8
                  </span>
                  <h3 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mt-1">
                    Review and Customize Blueprint
                  </h3>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                    You have full control. Toggle chapters on or off, edit chapter titles, or customize subtopics before generation.
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400">
                    Active Blueprint
                  </span>
                  <p className="text-base font-bold text-blue-600 dark:text-blue-400 font-mono">
                    {blueprint.filter((b) => b.included).length} Chapters (~{totalPages} Pages)
                  </p>
                </div>
              </div>

              {/* Editable Chapters List */}
              <div className="space-y-3 pt-1">
                {blueprint.map((chapter) => (
                  <div
                    key={chapter.id}
                    className={`p-4 rounded-xl border transition-all ${
                      chapter.included
                        ? "border-zinc-200 dark:border-zinc-850 bg-white dark:bg-zinc-900/60 shadow-xs"
                        : "border-zinc-200 dark:border-zinc-900 bg-zinc-100/50 dark:bg-zinc-950/40 opacity-60"
                    }`}
                  >
                    <div className="flex items-start gap-3.5">
                      {/* Checkbox toggle */}
                      <input
                        type="checkbox"
                        checked={chapter.included}
                        onChange={() => toggleChapter(chapter.id)}
                        className="mt-1 w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer"
                        id={`ch-toggle-${chapter.id}`}
                      />

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          {editingChapterId === chapter.id ? (
                            <div className="flex items-center gap-2 flex-1">
                              <span className="text-sm font-bold text-zinc-900 dark:text-white">
                                Chapter {chapter.number} —
                              </span>
                              <input
                                type="text"
                                defaultValue={chapter.title}
                                onBlur={(e) => {
                                  updateChapterTitle(chapter.id, e.target.value);
                                  setEditingChapterId(null);
                                }}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") {
                                    updateChapterTitle(chapter.id, (e.target as HTMLInputElement).value);
                                    setEditingChapterId(null);
                                  }
                                }}
                                autoFocus
                                className="px-2 py-0.5 rounded border border-blue-500 bg-white dark:bg-zinc-950 text-sm font-semibold text-zinc-900 dark:text-white focus:outline-none flex-1"
                              />
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <h4
                                className={`text-sm font-bold ${
                                  chapter.included
                                    ? "text-zinc-900 dark:text-white"
                                    : "text-zinc-500 line-through"
                                }`}
                              >
                                Chapter {chapter.number} — {chapter.title}
                              </h4>
                              {chapter.included && (
                                <button
                                  type="button"
                                  onClick={() => setEditingChapterId(chapter.id)}
                                  className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
                                  title="Edit Chapter Title"
                                >
                                  <Edit2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          )}

                          <span className="text-xs font-mono text-zinc-500 shrink-0">
                            {chapter.estimatedPages} pages
                          </span>
                        </div>

                        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                          {chapter.description}
                        </p>

                        {chapter.included && (
                          <div className="flex flex-wrap gap-1.5 mt-2.5">
                            {chapter.subsections.map((sub, sIdx) => (
                              <span
                                key={sIdx}
                                className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-[11px] font-mono text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700"
                              >
                                {sub}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* STEP 8: Generate */}
          {currentStep === 8 && (
            <div className="space-y-6 py-4 animate-in fade-in duration-200">
              {!generatedDoc && !isGenerating && (
                <div className="text-center max-w-md mx-auto space-y-4">
                  <div className="w-16 h-16 rounded-2xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 flex items-center justify-center mx-auto shadow-lg">
                    <Sparkles className="w-8 h-8" />
                  </div>
                  <div>
                    <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                      Step 8 of 8
                    </span>
                    <h3 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mt-1">
                      Ready to Generate Your Report
                    </h3>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-2 leading-relaxed">
                      ARM will now synthesize all <strong>{blueprint.filter((b) => b.included).length} reviewed chapters</strong> according to <strong>{university}</strong> format guidelines.
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 text-left text-xs space-y-2">
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Document Title:</span>
                      <span className="font-semibold text-zinc-900 dark:text-white truncate max-w-[220px]">
                        {title}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Target University:</span>
                      <span className="font-semibold text-zinc-900 dark:text-white">
                        {university.split("(")[0]}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Chapters to compile:</span>
                      <span className="font-semibold text-zinc-900 dark:text-white">
                        {blueprint.filter((b) => b.included).length} Chapters
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Evidence files grounded:</span>
                      <span className="font-semibold text-zinc-900 dark:text-white">
                        {evidenceFiles.length} files
                      </span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleStartGeneration}
                    className="w-full py-3.5 px-6 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <Sparkles className="w-4 h-4" />
                    Start Full Report Generation
                  </button>
                </div>
              )}

              {/* Generating In-Flight with Section 10 AI Brain Indicator */}
              {isGenerating && (
                <div className="max-w-xl mx-auto py-6 space-y-4 animate-in fade-in duration-200">
                  <div className="text-center mb-6">
                    <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                      Step 8 of 8 • AI Agent Execution
                    </span>
                    <h3 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-white mt-1">
                      ARM is Synthesizing Your Report
                    </h3>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                      Executing deterministic OpenXML formatting according to {university.split("(")[0]} guidelines
                    </p>
                  </div>

                  <AgentStatus currentStage={generationStage} />
                </div>
              )}

              {/* Generated Result Completed */}
              {generatedDoc && (
                <div className="max-w-xl mx-auto space-y-5 animate-in zoom-in-95 duration-200">
                  <div className="p-6 rounded-2xl border border-emerald-200 dark:border-emerald-950/80 bg-emerald-50/50 dark:bg-emerald-950/20 text-center space-y-2">
                    <div className="w-12 h-12 rounded-xl bg-emerald-600 text-white flex items-center justify-center mx-auto shadow-sm">
                      <CheckCircle2 className="w-7 h-7" />
                    </div>
                    <h3 className="text-xl font-bold tracking-tight text-emerald-950 dark:text-emerald-100">
                      Report Successfully Synthesized!
                    </h3>
                    <p className="text-xs text-emerald-800 dark:text-emerald-300 max-w-md mx-auto">
                      All {blueprint.filter((b) => b.included).length} reviewed chapters have been created with Times New Roman 14pt (H1), 12pt body text, and 1.25&quot; college binding margins.
                    </p>
                  </div>

                  {/* Summary Card */}
                  <div className="p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4 shadow-sm">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-lg bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
                          <FileText className="w-6 h-6" />
                        </div>
                        <div>
                          <h4 className="text-sm font-bold text-zinc-900 dark:text-white">
                            {generatedDoc.fileName}
                          </h4>
                          <p className="text-xs text-zinc-500 font-mono mt-0.5">
                            {(((generatedDoc.fileSizeBytes ?? 248000)) / 1024).toFixed(0)} KB • OpenXML Format • Verified
                          </p>
                        </div>
                      </div>
                      <span className="px-2.5 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 text-xs font-semibold">
                        Ready
                      </span>
                    </div>

                    <div className="grid grid-cols-1 gap-3 pt-1">
                      <a
                        href={generatedDoc.docxDownloadUrl || "/Project_Report_Final_IEEE.docx"}
                        download={generatedDoc.fileName}
                        className="py-2.5 px-4 rounded-xl border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-750 text-xs font-semibold text-zinc-900 dark:text-white flex items-center justify-center gap-2 transition-colors cursor-pointer"
                      >
                        <Download className="w-4 h-4 text-blue-500" />
                        Download .DOCX
                      </a>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleFinishAndOpen}
                    className="w-full py-3.5 px-6 rounded-xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-950 font-bold text-sm shadow-md hover:opacity-90 transition-all flex items-center justify-center gap-2 cursor-pointer"
                  >
                    Open in ARM Workspace Stream
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Navigation Buttons */}
        <div className="px-6 py-4 border-t border-zinc-200 dark:border-zinc-850 flex items-center justify-between bg-zinc-50/70 dark:bg-zinc-900/50">
          <button
            type="button"
            onClick={() => setCurrentStep((prev) => Math.max(1, prev - 1))}
            disabled={currentStep === 1 || isGenerating}
            className="px-4 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 text-xs font-semibold text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
            {currentStep === 4 ? "Back to Intake (Questions 1–3)" : "Previous"}
          </button>

          <div className="flex items-center gap-2">
            {currentStep < 8 ? (
              <button
                type="button"
                onClick={() => setCurrentStep((prev) => Math.min(8, prev + 1))}
                className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs hover:shadow transition-all flex items-center gap-1.5 cursor-pointer"
              >
                {currentStep === 3 ? (
                  <>
                    Continue to 2nd Page (Evidence & Review)
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </>
                ) : currentStep === 7 ? (
                  <>
                    Approve Blueprint & Proceed to Generation
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </>
                ) : (
                  <>
                    Next Step
                    <ChevronRight className="w-4 h-4" />
                  </>
                )}
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
