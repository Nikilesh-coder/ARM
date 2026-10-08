/**
 * ReportForge AI - Isolated Mock & Demo Fallbacks
 *
 * ATTENTION:
 * This file contains strictly isolated mock fallbacks for UI demonstrations
 * and empty state populating before live backend database syncing.
 * It is completely decoupled from the production API client.
 */

export interface ProjectItem {
  id: string;
  title: string;
  projectType: "capstone" | "seminar" | "internship" | "thesis" | "weekly_lab";
  academicYear: string;
  guideName: string;
  abstractSummary: string;
  techStack: string[];
  status: "draft" | "in_progress" | "review" | "ready";
  templateName: string;
  evidenceCount: number;
  updatedAt: string;
}

export interface TemplateItem {
  id: string;
  name: string;
  institution: string;
  pageSize: string;
  margins: string;
  defaultFont: string;
  sectionCount: number;
  confidenceScore: number;
  status: "verified" | "pending_review" | "preset";
  updatedAt: string;
}

export interface EvidenceItem {
  id: string;
  fileName: string;
  fileType: "screenshot" | "database_schema" | "code_snippet" | "dataset_csv" | "diagram";
  fileSize: string;
  targetSection: string;
  status: "mapped" | "parsed" | "pending";
  uploadedAt: string;
}

export interface ReportItem {
  id: string;
  projectTitle: string;
  reportType: string;
  version: string;
  status: "planned" | "generating" | "validated" | "compiled";
  completionPercentage: number;
  wordCount: number;
  citationCount: number;
  docxAvailable: boolean;
  pdfAvailable: boolean;
  updatedAt: string;
}

export interface WeeklyReportItem {
  id: string;
  weekNumber: number;
  dateRange: string;
  plannedTasks: string;
  completedTasks: string;
  blockers: string;
  status: "submitted" | "approved" | "draft";
}

export const INITIAL_MOCK_PROJECTS: ProjectItem[] = [
  {
    id: "proj-capstone-01",
    title: "Autonomous Academic Report Synthesizer with OpenXML Compliance",
    projectType: "capstone",
    academicYear: "2026-2027",
    guideName: "Dr. Sarah Jenkins, Dept. of Computer Science",
    abstractSummary: "An automated academic documentation engine eliminating formatting overhead for engineering reports.",
    techStack: ["FastAPI", "Next.js", "Python-docx", "OpenXML", "Supabase", "Gemini 2.5"],
    status: "in_progress",
    templateName: "VTU_BTech_Final_Template_2026.docx",
    evidenceCount: 7,
    updatedAt: "2 hours ago",
  },
  {
    id: "proj-seminar-02",
    title: "Modern Architectures in Retrieval-Augmented Generation for Scientific Literature",
    projectType: "seminar",
    academicYear: "2026-2027",
    guideName: "Prof. Rajesh Kumar",
    abstractSummary: "Comparative study on hallucination reduction techniques in technical documentation.",
    techStack: ["PyTorch", "HuggingFace", "FastAPI"],
    status: "ready",
    templateName: "IEEE_Conference_2Column.docx",
    evidenceCount: 4,
    updatedAt: "1 day ago",
  },
  {
    id: "proj-intern-03",
    title: "Cloud Infrastructure Cost Optimization at FinTech Scale",
    projectType: "internship",
    academicYear: "2026-2027",
    guideName: "Industry Mentor: Alex Rivera",
    abstractSummary: "Comprehensive 8-week internship report summarizing AWS Graviton migration metrics.",
    techStack: ["AWS", "Terraform", "Docker", "Prometheus"],
    status: "draft",
    templateName: "College_Internship_Report_v2.docx",
    evidenceCount: 5,
    updatedAt: "3 days ago",
  },
];

export const INITIAL_MOCK_TEMPLATES: TemplateItem[] = [
  {
    id: "tpl-vtu-01",
    name: "VTU B.Tech Capstone Project Standard Template",
    institution: "Visvesvaraya Technological University",
    pageSize: "A4 Portrait (210 x 297 mm)",
    margins: "Left: 31.75mm (1.25 in), Others: 25.4mm (1.0 in)",
    defaultFont: "Times New Roman (12pt, 1.5 spacing)",
    sectionCount: 12,
    confidenceScore: 0.98,
    status: "verified",
    updatedAt: "Verified Master",
  },
  {
    id: "tpl-anna-02",
    name: "Anna University Project Work Guidelines Format",
    institution: "Anna University, Chennai",
    pageSize: "A4 Portrait",
    margins: "Left: 35mm, Right: 25mm, Top/Bottom: 25mm",
    defaultFont: "Times New Roman (12pt, Double Spacing)",
    sectionCount: 10,
    confidenceScore: 0.95,
    status: "verified",
    updatedAt: "Verified Master",
  },
  {
    id: "tpl-custom-03",
    name: "MIT Autonomous Systems Lab Seminar Format",
    institution: "Department Preset",
    pageSize: "Letter Portrait",
    margins: "Standard 1-inch uniform",
    defaultFont: "Calibri (11.5pt, 1.15 spacing)",
    sectionCount: 8,
    confidenceScore: 0.91,
    status: "pending_review",
    updatedAt: "Uploaded 4 hours ago",
  },
];

export const INITIAL_MOCK_EVIDENCE: EvidenceItem[] = [
  {
    id: "ev-01",
    fileName: "system_architecture_diagram.png",
    fileType: "diagram",
    fileSize: "2.4 MB",
    targetSection: "Chapter 3: System Architecture → Figure 3.1",
    status: "mapped",
    uploadedAt: "Today, 10:24 AM",
  },
  {
    id: "ev-02",
    fileName: "postgresql_schema_v2.sql",
    fileType: "database_schema",
    fileSize: "48 KB",
    targetSection: "Chapter 3: Database Design → Section 3.4",
    status: "parsed",
    uploadedAt: "Yesterday",
  },
  {
    id: "ev-03",
    fileName: "latency_benchmark_comparison.csv",
    fileType: "dataset_csv",
    fileSize: "128 KB",
    targetSection: "Chapter 5: Results & Discussion → Table 5.1",
    status: "mapped",
    uploadedAt: "Yesterday",
  },
  {
    id: "ev-04",
    fileName: "auth_service_implementation.py",
    fileType: "code_snippet",
    fileSize: "16 KB",
    targetSection: "Chapter 4: Implementation Details → Listing 4.2",
    status: "parsed",
    uploadedAt: "2 days ago",
  },
  {
    id: "ev-05",
    fileName: "dashboard_ui_screenshot.png",
    fileType: "screenshot",
    fileSize: "1.8 MB",
    targetSection: "Chapter 4: User Interface Flow → Figure 4.3",
    status: "mapped",
    uploadedAt: "3 days ago",
  },
];

export const INITIAL_MOCK_REPORTS: ReportItem[] = [
  {
    id: "rep-01",
    projectTitle: "Autonomous Academic Report Synthesizer",
    reportType: "Final Capstone Documentation",
    version: "v1.2-draft",
    status: "validated",
    completionPercentage: 92,
    wordCount: 8450,
    citationCount: 24,
    docxAvailable: true,
    pdfAvailable: true,
    updatedAt: "Today, 11:45 AM",
  },
  {
    id: "rep-02",
    projectTitle: "Modern Architectures in Scientific RAG",
    reportType: "Technical Seminar Monograph",
    version: "v1.0-final",
    status: "compiled",
    completionPercentage: 100,
    wordCount: 4200,
    citationCount: 18,
    docxAvailable: true,
    pdfAvailable: true,
    updatedAt: "Yesterday",
  },
];

export const INITIAL_MOCK_WEEKLY_REPORTS: WeeklyReportItem[] = [
  {
    id: "wk-08",
    weekNumber: 8,
    dateRange: "Sep 22, 2026 – Sep 28, 2026",
    plannedTasks: "Complete OpenXML table rendering engine and integrate deterministic Roman numeral front-matter generator.",
    completedTasks: "Implemented TemplateParser AST extractor with 100% margin precision. Validated pytest test cases on sample templates.",
    blockers: "Minor line-spacing discrepancy in Word 2016 compatibility mode resolved.",
    status: "submitted",
  },
  {
    id: "wk-07",
    weekNumber: 7,
    dateRange: "Sep 15, 2026 – Sep 21, 2026",
    plannedTasks: "Setup FastAPI backend micro-architecture and PostgreSQL migration scripts.",
    completedTasks: "Completed clean domain services, RLS policies, and structured exception handlers.",
    blockers: "None",
    status: "approved",
  },
  {
    id: "wk-06",
    weekNumber: 6,
    dateRange: "Sep 08, 2026 – Sep 14, 2026",
    plannedTasks: "Finalize system requirements and architecture blueprint.",
    completedTasks: "Approved template-first thesis generation model and non-hallucinating citation rules.",
    blockers: "None",
    status: "approved",
  },
];
