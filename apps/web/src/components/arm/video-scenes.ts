export interface SceneConfig {
  id: number;
  key: string;
  title: string;
  subtitle: string;
  startTime: number;
  duration: number;
}

export const SCENES: SceneConfig[] = [
  { id: 1, key: "intro", title: "ARM Intro", subtitle: "Welcome to ARM", startTime: 0, duration: 3.2 },
  { id: 2, key: "model", title: "Meet ARM", subtitle: "AI-Powered Academic Assistant", startTime: 3.2, duration: 3.0 },
  { id: 3, key: "personalized", title: "Personalized Access", subtitle: "Dynamic Scholar Session", startTime: 6.2, duration: 3.0 },
  { id: 4, key: "dashboard", title: "Dashboard Tour", subtitle: "Full Academic Workspace", startTime: 9.2, duration: 3.3 },
  { id: 5, key: "create_project", title: "Project Setup", subtitle: "Student Project Intake", startTime: 12.5, duration: 3.3 },
  { id: 6, key: "upload_template", title: "Upload Template", subtitle: "College .DOCX Intake", startTime: 15.8, duration: 3.0 },
  { id: 7, key: "analysis", title: "Structure Analysis", subtitle: "Preserving College Rules", startTime: 18.8, duration: 3.4 },
  { id: 8, key: "evidence", title: "Add Evidence", subtitle: "Multimodal Research Assets", startTime: 22.2, duration: 3.0 },
  { id: 9, key: "thinking", title: "ARM AI Synthesis", subtitle: "Context-Aware Processing", startTime: 25.2, duration: 3.2 },
  { id: 10, key: "replacement", title: "Intelligent Replacement", subtitle: "Content Replaced • Layout Kept", startTime: 28.4, duration: 4.6 },
  { id: 11, key: "comparison", title: "Before & After", subtitle: "Same Template, New Content", startTime: 33.0, duration: 3.2 },
  { id: 12, key: "generation", title: "Report Generation", subtitle: "Final DOCX & PDF Assembly", startTime: 36.2, duration: 2.8 },
  { id: 13, key: "hero", title: "Hero Finale", subtitle: "Academic Report Made Intelligent", startTime: 39.0, duration: 3.5 },
];

export const TOTAL_VIDEO_DURATION = 42.5;
