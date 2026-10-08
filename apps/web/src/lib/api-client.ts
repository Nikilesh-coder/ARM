/**
 * ReportForge AI - Production TypeScript API Client
 * Centralized HTTP client for communicating with the FastAPI backend.
 * Stage 5: Project Information + Evidence Locker + Readiness
 */

export interface HealthResponse {
  status: "healthy" | string;
}

export interface DetailedHealthResponse {
  status: string;
  service: string;
  environment: string;
  timestamp: string;
  subsystems: {
    database: {
      status: string;
      provider: string;
      database_configured: boolean;
    };
    storage: {
      provider: string;
      configured: boolean;
    };
    ai: {
      provider: string;
      configured: boolean;
    };
  };
}

export interface ProjectLatestReportDTO {
  id?: string;
  title?: string;
  version?: number;
  status?: string;
  approval_status?: "pending" | "approved";
  approved_at?: string | null;
  word_count?: number;
  page_count?: number;
  docx_url?: string;
  pdf_url?: string;
  updated_at?: string;
}

export interface ProjectDTO {
  id?: string;
  user_id?: string;
  owner_id?: string;
  project_name?: string;
  title: string;
  report_title?: string;
  report_type?: string;
  project_type: "capstone" | "seminar" | "internship" | "weekly_lab" | "thesis" | string;
  description?: string;
  academic_year?: string;
  department?: string;
  institution?: string;
  semester?: string;
  guide_name?: string;
  abstract_summary?: string;
  problem_statement?: string;
  objectives?: string;
  scope?: string;
  methodology?: string;
  expected_outcome?: string;
  actual_outcome?: string;
  start_date?: string;
  end_date?: string;
  additional_notes?: string;
  instructions?: string;
  template_id?: string;
  template_name?: string;
  generation_status?: string;
  latest_report?: ProjectLatestReportDTO | null;
  latest_job_id?: string | null;
  is_team_project?: boolean;
  target_page_count?: number;
  tech_stack?: string[];
  status?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TemplateDTO {
  id: string;
  project_id?: string;
  user_id?: string;
  name: string;
  original_file_path?: string;
  file_type?: string;
  file_size?: number;
  file_size_bytes?: number;
  status?: string;
  analysis_status?: string;
  is_locked?: boolean;
  is_institution_preset?: boolean;
  is_master?: boolean;
  institution?: string;
  department?: string;
  owner_id?: string;
  report_type?: string;
  page_settings?: {
    width_in?: number;
    height_in?: number;
    orientation?: string;
    top_margin_in?: number;
    bottom_margin_in?: number;
    left_margin_in?: number;
    right_margin_in?: number;
  };
  field_mapping?: any[];
  image_mapping?: any[];
  created_at?: string;
  updated_at?: string;
}

export interface TemplateFieldDTO {
  id?: string;
  template_id: string;
  field_key?: string;
  field_name: string;
  field_label?: string;
  field_type: "text" | "long_text" | "image" | "table" | "list" | string;
  section_key?: string;
  page_or_section?: string;
  is_required?: boolean;
  placeholder_identifier?: string;
  content_limits?: {
    min_words?: number;
    max_words?: number;
    min_length?: number;
    max_length?: number;
    min_items?: number;
    max_items?: number;
    [key: string]: any;
  };
  image_dimensions?: {
    width?: number;
    height?: number;
    aspect_ratio?: string;
    dpi?: number;
    [key: string]: any;
  };
  ordering?: number;
  max_length?: number;
  bounding_box?: Record<string, any>;
  default_value?: string;
  metadata?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface MasterTemplateResponseDTO {
  id: string;
  name: string;
  is_master: boolean;
  is_locked: boolean;
  status: string;
  master_version: string;
  description?: string;
  institution?: string;
  department?: string;
  fields_count: number;
  fields: TemplateFieldDTO[];
}

export interface GeneratedContentDTO {
  id?: string;
  report_id: string;
  project_id: string;
  user_id?: string;
  section_key: string;
  field_key?: string;
  content_type?: string;
  raw_content: string;
  formatted_content?: string;
  word_count?: number;
  character_count?: number;
  token_count?: number;
  confidence_score?: number;
  status?: "draft" | "verified" | "approved" | "rejected" | string;
  version_number?: number;
  metadata?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface ReportAssetDTO {
  id?: string;
  report_id: string;
  project_id: string;
  user_id?: string;
  asset_type: "image" | "diagram" | "chart" | "canva_asset" | "evidence_photo" | "logo" | string;
  title: string;
  caption?: string;
  file_name: string;
  storage_path: string;
  mime_type?: string;
  file_size_bytes?: number;
  source_evidence_id?: string;
  section_key?: string;
  field_key?: string;
  metadata?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface ReportRecordDTO {
  id: string;
  project_id: string;
  template_id?: string;
  title: string;
  report_type?: string;
  current_version: number;
  status: string;
  docx_storage_path?: string;
  pdf_storage_path?: string;
  user_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectMemberDTO {
  id: string;
  project_id: string;
  user_id?: string;
  name: string;
  roll_number?: string;
  email?: string;
  role: string;
  created_at?: string;
  updated_at?: string;
}

export interface EvidenceDTO {
  id: string;
  project_id: string;
  user_id?: string;
  file_name: string;
  file_type: string;
  mime_type?: string;
  file_size_bytes: number;
  storage_path: string;
  sha256_hash?: string;
  category: "dataset" | "code_sample" | "survey_results" | "notes" | "literature" | "system_output" | "other" | string;
  description?: string;
  upload_status: string;
  metadata?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectReadinessDTO {
  project_id: string;
  template_locked: boolean;
  info_completed: boolean;
  evidence_count: number;
  members_count: number;
  is_ready_for_generation: boolean;
  missing_fields: string[];
  completion_percentage: number;
}

export interface TemplateUploadResult {
  template_id: string;
  name: string;
  file_size_bytes: number;
  is_preset?: boolean;
  status: string;
  message: string;
  file_type?: string;
  project_id?: string;
  original_file_path?: string;
  analysis_status?: string;
}

export interface SectionPlan {
  section_key: string;
  title: string;
  sequence_order: number;
  level: number;
  mandatory: boolean;
  estimated_word_count: number;
}

export interface ReportPlanResponse {
  report_id: string;
  project_id: string;
  template_id: string;
  title: string;
  status: string;
  sections: SectionPlan[];
  created_at: string;
}

export class ApiError extends Error {
  code: string;
  status: number;
  details?: any;

  constructor(message: string, code = "API_ERROR", status = 500, details?: any) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

class ReportForgeClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
    const headers = new Headers(options.headers || {});

    if (!headers.has("Authorization") && typeof window !== "undefined") {
      try {
        const { supabase } = await import("@/lib/supabase");
        const session = (await supabase.auth.getSession()).data.session;
        if (session?.access_token) {
          headers.set("Authorization", `Bearer ${session.access_token}`);
        } else {
          const storedId = localStorage.getItem("arm_user_id");
          if (storedId) {
            headers.set("Authorization", `Bearer ${storedId}`);
          }
        }
      } catch {}
    }

    if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errData: any = {};
        try {
          errData = await response.json();
        } catch {
          // non-JSON error
        }

        const errDetail = errData.error || errData || {};
        throw new ApiError(
          errDetail.message || errData.detail || `Request failed with status ${response.status}`,
          errDetail.code || "HTTP_ERROR",
          response.status,
          errDetail.details
        );
      }

      return (await response.json()) as T;
    } catch (err: any) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(err.message || "Network request failed", "NETWORK_ERROR", 0);
    }
  }

  // --- Health Endpoints ---
  async checkHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  async getDetailedHealth(): Promise<DetailedHealthResponse> {
    return this.request<DetailedHealthResponse>("/api/v1/health");
  }

  // --- Project Endpoints ---
  async createProject(project: Partial<ProjectDTO>): Promise<ProjectDTO> {
    return this.request<ProjectDTO>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify(project),
    });
  }

  async getProjects(): Promise<ProjectDTO[]> {
    return this.request<ProjectDTO[]>("/api/v1/projects");
  }

  async getProject(projectId: string): Promise<ProjectDTO> {
    return this.request<ProjectDTO>(`/api/v1/projects/${projectId}`);
  }

  async updateProject(projectId: string, data: Partial<ProjectDTO>): Promise<ProjectDTO> {
    return this.request<ProjectDTO>(`/api/v1/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteProject(projectId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}`, {
      method: "DELETE",
    });
  }

  async regenerateProject(projectId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/regenerate`, {
      method: "POST",
    });
  }

  async getProjectReadiness(projectId: string): Promise<ProjectReadinessDTO> {
    return this.request<ProjectReadinessDTO>(`/api/v1/projects/${projectId}/readiness`);
  }

  // --- Project Members Endpoints ---
  async getProjectMembers(projectId: string): Promise<ProjectMemberDTO[]> {
    return this.request<ProjectMemberDTO[]>(`/api/v1/projects/${projectId}/members`);
  }

  async addProjectMember(
    projectId: string,
    member: { name: string; roll_number?: string; email?: string; role?: string }
  ): Promise<ProjectMemberDTO> {
    return this.request<ProjectMemberDTO>(`/api/v1/projects/${projectId}/members`, {
      method: "POST",
      body: JSON.stringify(member),
    });
  }

  async updateProjectMember(
    projectId: string,
    memberId: string,
    member: Partial<ProjectMemberDTO>
  ): Promise<ProjectMemberDTO> {
    return this.request<ProjectMemberDTO>(`/api/v1/projects/${projectId}/members/${memberId}`, {
      method: "PATCH",
      body: JSON.stringify(member),
    });
  }

  async deleteProjectMember(projectId: string, memberId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/members/${memberId}`, {
      method: "DELETE",
    });
  }

  // --- Evidence Locker Endpoints ---
  async getProjectEvidence(projectId: string, category?: string): Promise<EvidenceDTO[]> {
    const url = category
      ? `/api/v1/projects/${projectId}/evidence?category=${encodeURIComponent(category)}`
      : `/api/v1/projects/${projectId}/evidence`;
    return this.request<EvidenceDTO[]>(url);
  }

  async uploadProjectEvidence(
    projectId: string,
    file: File,
    category?: string,
    description?: string
  ): Promise<EvidenceDTO> {
    const formData = new FormData();
    formData.append("file", file);
    if (category) formData.append("category", category);
    if (description) formData.append("description", description);

    return this.request<EvidenceDTO>(`/api/v1/projects/${projectId}/evidence`, {
      method: "POST",
      body: formData,
    });
  }

  async getEvidenceDetails(projectId: string, evidenceId: string): Promise<EvidenceDTO> {
    return this.request<EvidenceDTO>(`/api/v1/projects/${projectId}/evidence/${evidenceId}`);
  }

  async updateEvidenceDetails(
    projectId: string,
    evidenceId: string,
    payload: { category?: string; description?: string }
  ): Promise<EvidenceDTO> {
    return this.request<EvidenceDTO>(`/api/v1/projects/${projectId}/evidence/${evidenceId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  }

  async deleteProjectEvidence(projectId: string, evidenceId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/evidence/${evidenceId}`, {
      method: "DELETE",
    });
  }

  getEvidenceDownloadUrl(projectId: string, evidenceId: string): string {
    return `${this.baseUrl}/api/v1/projects/${projectId}/evidence/${evidenceId}/download`;
  }

  // --- Template Endpoints ---
  async getMasterTemplate(): Promise<MasterTemplateResponseDTO> {
    return this.request<MasterTemplateResponseDTO>("/api/v1/templates/master");
  }

  async getTemplates(): Promise<TemplateDTO[]> {
    return this.request<TemplateDTO[]>("/api/v1/templates");
  }

  async getTemplateFields(templateId: string): Promise<TemplateFieldDTO[]> {
    return this.request<TemplateFieldDTO[]>(`/api/v1/templates/${templateId}/fields`);
  }

  async createProjectReport(projectId: string, report: { title: string; template_id?: string; report_type?: string }): Promise<ReportRecordDTO> {
    return this.request<ReportRecordDTO>(`/api/v1/projects/${projectId}/reports`, {
      method: "POST",
      body: JSON.stringify(report),
    });
  }

  async getProjectReports(projectId: string): Promise<ReportRecordDTO[]> {
    return this.request<ReportRecordDTO[]>(`/api/v1/projects/${projectId}/reports`);
  }

  async uploadCustomCollegeTemplate(
    file: File,
    meta: { name: string; institution?: string; department?: string; report_type?: string }
  ): Promise<any> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", meta.name);
    if (meta.institution) formData.append("institution", meta.institution);
    if (meta.department) formData.append("department", meta.department);
    if (meta.report_type) formData.append("report_type", meta.report_type);

    return this.request<any>("/api/v1/templates/upload-custom", {
      method: "POST",
      body: formData,
    });
  }

  async getCustomTemplateDetails(templateId: string): Promise<any> {
    return this.request<any>(`/api/v1/templates/${templateId}`);
  }

  async updateCustomTemplateMapping(
    templateId: string,
    payload: { field_mapping: any[]; image_mapping?: any[] }
  ): Promise<any> {
    return this.request<any>(`/api/v1/templates/${templateId}/mapping`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async deleteCustomTemplate(templateId: string): Promise<any> {
    return this.request<any>(`/api/v1/templates/${templateId}`, {
      method: "DELETE",
    });
  }

  async uploadTemplate(file: File): Promise<TemplateUploadResult> {
    const formData = new FormData();
    formData.append("file", file);

    return this.request<TemplateUploadResult>("/api/v1/templates/upload", {
      method: "POST",
      body: formData,
    });
  }

  async uploadProjectTemplate(projectId: string, file: File): Promise<TemplateUploadResult> {
    const formData = new FormData();
    formData.append("file", file);

    return this.request<TemplateUploadResult>(`/api/v1/projects/${projectId}/templates/upload`, {
      method: "POST",
      body: formData,
    });
  }

  async getProjectTemplate(projectId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/template`);
  }

  async analyzeProjectTemplate(projectId: string, templateId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/templates/${templateId}/analyze`, {
      method: "POST",
    });
  }

  async getProjectTemplateAnalysis(projectId: string, templateId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/templates/${templateId}/analysis`);
  }

  async getProjectTemplateReview(projectId: string, templateId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/templates/${templateId}/review`);
  }

  async patchProjectTemplateReview(projectId: string, templateId: string, payload: { reviewed_schema: any; notes?: string }): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/templates/${templateId}/review`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  }

  async lockProjectTemplate(projectId: string, templateId: string, payload?: { confirm?: boolean; notes?: string }): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/templates/${templateId}/lock`, {
      method: "POST",
      body: JSON.stringify(payload || { confirm: true }),
    });
  }

  async getProjectTemplateLockedSchema(projectId: string, templateId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/templates/${templateId}/locked-schema`);
  }

  async getProjectTemplateJob(projectId: string, templateId: string, jobId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/templates/${templateId}/jobs/${jobId}`);
  }

  async deleteProjectTemplate(projectId: string, templateId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/templates/${templateId}`, {
      method: "DELETE",
    });
  }

  async getTemplateSchema(templateId: string): Promise<any> {
    return this.request<any>(`/api/v1/templates/${templateId}/schema`);
  }

  // --- Report Planning Endpoints ---
  async createReportPlan(data: {
    project_id: string;
    template_id: string;
    report_title: string;
    report_type: string;
  }): Promise<ReportPlanResponse> {
    return this.request<ReportPlanResponse>("/api/v1/reports/plan", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getReportPlan(reportId: string): Promise<ReportPlanResponse> {
    return this.request<ReportPlanResponse>(`/api/v1/reports/${reportId}/plan`);
  }

  // --- Stage 6 AI Report Planner Endpoints ---
  async planProjectReport(
    projectId: string,
    options?: { force?: boolean; target_page_count?: number }
  ): Promise<ReportPlanDTO> {
    const params = new URLSearchParams();
    if (options?.force) params.set("force", "true");
    params.set("sync", "true");
    const qs = params.toString() ? `?${params.toString()}` : "";
    return this.request<ReportPlanDTO>(`/api/v1/projects/${projectId}/report-plan${qs}`, {
      method: "POST",
      body: JSON.stringify({
        force: options?.force,
        target_page_count: options?.target_page_count,
      }),
    });
  }

  async getProjectReportPlan(projectId: string): Promise<ReportPlanDTO> {
    return this.request<ReportPlanDTO>(`/api/v1/projects/${projectId}/report-plan`);
  }

  async approveProjectReportPlan(projectId: string, planId?: string): Promise<ReportPlanDTO> {
    return this.request<ReportPlanDTO>(`/api/v1/projects/${projectId}/report-plan/approve`, {
      method: "POST",
      body: JSON.stringify({ plan_id: planId }),
    });
  }

  async getProjectPlanningJob(projectId: string, jobId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/report-plan/jobs/${jobId}`);
  }

  // --- Stage 7 AI Section-by-Section Report Generation ---
  async generateProjectReport(projectId: string, options?: { force?: boolean }): Promise<GeneratedReportDTO> {
    const params = new URLSearchParams();
    if (options?.force) params.set("force", "true");
    const qs = params.toString() ? `?${params.toString()}` : "";
    return this.request<GeneratedReportDTO>(`/api/v1/projects/${projectId}/generate-report${qs}`, {
      method: "POST",
      body: JSON.stringify({ force: options?.force }),
    });
  }

  async getLatestProjectReport(projectId: string): Promise<GeneratedReportDTO> {
    return this.request<GeneratedReportDTO>(`/api/v1/projects/${projectId}/report`);
  }

  async getProjectReportVersions(projectId: string): Promise<any[]> {
    return this.request<any[]>(`/api/v1/projects/${projectId}/report/versions`);
  }

  async getProjectReportVersion(projectId: string, versionNumber: number): Promise<GeneratedReportDTO> {
    return this.request<GeneratedReportDTO>(`/api/v1/projects/${projectId}/report/versions/${versionNumber}`);
  }

  async getReportGenerationJob(projectId: string, jobId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/report/jobs/${jobId}`);
  }

  // --- Stage 8 Citation + Evidence Verification ---
  async verifyProjectReport(projectId: string, versionNumber?: number): Promise<ReportVerificationReportDTO> {
    const qs = versionNumber ? `?version_number=${versionNumber}` : "";
    return this.request<ReportVerificationReportDTO>(`/api/v1/projects/${projectId}/report/verify${qs}`, {
      method: "POST",
    });
  }

  async getLatestProjectVerification(projectId: string): Promise<ReportVerificationReportDTO | null> {
    return this.request<ReportVerificationReportDTO | null>(`/api/v1/projects/${projectId}/report/verification`);
  }

  async getVersionProjectVerification(projectId: string, versionNumber: number): Promise<ReportVerificationReportDTO> {
    return this.request<ReportVerificationReportDTO>(`/api/v1/projects/${projectId}/report/versions/${versionNumber}/verification`);
  }

  async getReportVerificationJob(projectId: string, jobId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/report/verification/jobs/${jobId}`);
  }

  // --- Stage 9 Deterministic DOCX Generation Engine ---
  async compileProjectDocx(
    projectId: string,
    options?: { version_number?: number; force?: boolean }
  ): Promise<any> {
    const params = new URLSearchParams();
    if (options?.version_number !== undefined) params.set("version_number", String(options.version_number));
    if (options?.force) params.set("force", "true");
    const qs = params.toString() ? `?${params.toString()}` : "";
    return this.request<any>(`/api/v1/projects/${projectId}/report/compile-docx${qs}`, {
      method: "POST",
      body: JSON.stringify({
        version_number: options?.version_number,
        force: options?.force,
      }),
    });
  }

  getDocxDownloadUrl(projectId: string, versionNumber?: number): string {
    const base = this.baseUrl || "";
    const qs = versionNumber !== undefined ? `?version_number=${versionNumber}` : "";
    return `${base}/api/v1/projects/${projectId}/report/download-docx${qs}`;
  }

  async downloadProjectDocxBlob(projectId: string, versionNumber?: number): Promise<{ blob: Blob; filename: string }> {
    const url = this.getDocxDownloadUrl(projectId, versionNumber);
    const res = await fetch(url);
    if (!res.ok) {
      let errMsg = "Failed to download compiled DOCX.";
      try {
        const errJson = await res.json();
        errMsg = errJson.detail || errMsg;
      } catch {}
      throw new Error(errMsg);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition");
    let filename = "Report.docx";
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) filename = match[1];
    }
    return { blob, filename };
  }

  async getDocumentGenerationJob(projectId: string, jobId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/report/document/jobs/${jobId}`);
  }

  // --- Stage 10 Server-Side PDF Generation Engine ---
  async compileProjectPdf(projectId: string, versionNumber?: number): Promise<any> {
    const qs = versionNumber !== undefined ? `?version_number=${versionNumber}` : "";
    return this.request<any>(`/api/v1/projects/${projectId}/report/compile-pdf${qs}`, {
      method: "POST",
      body: JSON.stringify({ version_number: versionNumber }),
    });
  }

  getPdfDownloadUrl(projectId: string, versionNumber?: number): string {
    const base = this.baseUrl || "";
    const qs = versionNumber !== undefined ? `?version_number=${versionNumber}` : "";
    return `${base}/api/v1/projects/${projectId}/report/download-pdf${qs}`;
  }

  async downloadProjectPdfBlob(projectId: string, versionNumber?: number): Promise<{ blob: Blob; filename: string }> {
    const url = this.getPdfDownloadUrl(projectId, versionNumber);
    const res = await fetch(url);
    if (!res.ok) {
      let errMsg = "Failed to download compiled PDF.";
      try {
        const errJson = await res.json();
        errMsg = errJson.detail || errMsg;
      } catch {}
      throw new Error(errMsg);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition");
    let filename = "Report.pdf";
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) filename = match[1];
    }
    return { blob, filename };
  }

  async getPdfGenerationJob(projectId: string, jobId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/report/pdf/jobs/${jobId}`);
  }

  // --- Stage 11 Report Validation & Quality Engine ---
  async validateProjectReport(
    projectId: string,
    options?: { version_number?: number; force_revalidate?: boolean }
  ): Promise<ReportQualityResultDTO> {
    return this.request<ReportQualityResultDTO>(`/api/v1/projects/${projectId}/report/validate`, {
      method: "POST",
      body: JSON.stringify({
        version_number: options?.version_number,
        force_revalidate: options?.force_revalidate,
      }),
    });
  }

  async getLatestProjectValidation(projectId: string): Promise<ReportQualityResultDTO | null> {
    return this.request<ReportQualityResultDTO | null>(`/api/v1/projects/${projectId}/report/validation`);
  }

  async getVersionProjectValidation(projectId: string, versionNumber: number): Promise<ReportQualityResultDTO> {
    return this.request<ReportQualityResultDTO>(`/api/v1/projects/${projectId}/report/validation?version_number=${versionNumber}`);
  }

  async getReportValidationJob(projectId: string, jobId: string): Promise<any> {
    return this.request<any>(`/api/v1/projects/${projectId}/report/validation/jobs/${jobId}`);
  }

  // --- ARM AI Report Agent Endpoints ---
  async generateAgentReportContent(input: AIReportAgentInputDTO): Promise<AIReportAgentOutputDTO> {
    return this.request<AIReportAgentOutputDTO>("/api/v1/agent/generate-report-content", {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  async getAgentJobStatus(jobId: string): Promise<AgentJobStatusDTO> {
    return this.request<AgentJobStatusDTO>(`/api/v1/agent/status/${jobId}`);
  }

  // --- ARM Automatic Image System Endpoints ---
  async determineImageRequirements(
    projectId: string,
    data: {
      project_title: string;
      project_description: string;
      template_id?: string;
      image_fields?: string[];
    }
  ): Promise<DetermineImageRequirementsResponseDTO> {
    return this.request<DetermineImageRequirementsResponseDTO>(`/api/v1/projects/${projectId}/assets/determine-requirements`, {
      method: "POST",
      body: JSON.stringify({
        project_id: projectId,
        project_title: data.project_title,
        project_description: data.project_description,
        template_id: data.template_id,
        image_fields: data.image_fields,
      }),
    });
  }

  async runAutomaticImagePipeline(
    projectId: string,
    data?: {
      report_id?: string;
      project_title?: string;
      project_description?: string;
      template_id?: string;
      target_fields?: string[];
      preferred_provider?: string;
      force_regenerate?: boolean;
    }
  ): Promise<AutomaticImagePipelineResponseDTO> {
    return this.request<AutomaticImagePipelineResponseDTO>(`/api/v1/projects/${projectId}/automatic-images`, {
      method: "POST",
      body: JSON.stringify({
        project_id: projectId,
        ...(data || {}),
      }),
    });
  }

  async getProjectAssets(projectId: string): Promise<ReportAssetItemDTO[]> {
    return this.request<ReportAssetItemDTO[]>(`/api/v1/projects/${projectId}/assets`);
  }

  async executeTemplateReplacement(data: ReplacementExecutionRequestDTO): Promise<ReplacementJobResponseDTO> {
    return this.request<ReplacementJobResponseDTO>("/api/v1/replacement/execute", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getReplacementStatus(jobId: string): Promise<ReplacementJobResponseDTO> {
    return this.request<ReplacementJobResponseDTO>(`/api/v1/replacement/status/${jobId}`);
  }

  async getReplacementPreview(jobId: string): Promise<ReplacementPreviewResponseDTO> {
    return this.request<ReplacementPreviewResponseDTO>(`/api/v1/replacement/preview/${jobId}`);
  }

  getReplacementDownloadUrl(jobId: string, format: "docx" | "pdf" = "docx"): string {
    return `${this.baseUrl}/api/v1/replacement/download/${jobId}?format=${format}`;
  }

  async getMasterCollegeTemplate(): Promise<any> {
    return this.request<any>("/api/v1/replacement/master-template");
  }

  // --- ARM Report Preview Workflow Actions ---
  async regenerateReportSection(data: {
    job_id: string;
    section_name: string;
    custom_prompt?: string;
  }): Promise<ReplacementJobResponseDTO> {
    return this.request<ReplacementJobResponseDTO>("/api/v1/replacement/regenerate-section", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async replaceReportImage(data: {
    job_id: string;
    image_slot: string;
    asset_path?: string;
    image_base64?: string;
    caption?: string;
  }): Promise<ReplacementJobResponseDTO> {
    return this.request<ReplacementJobResponseDTO>("/api/v1/replacement/replace-image", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async approveReplacementReport(jobId: string): Promise<ReplacementJobResponseDTO> {
    return this.request<ReplacementJobResponseDTO>(`/api/v1/replacement/approve/${jobId}`, {
      method: "POST",
    });
  }

  async regenerateReplacementReport(
    jobId: string,
    userInstructions?: string
  ): Promise<ReplacementJobResponseDTO> {
    return this.request<ReplacementJobResponseDTO>(`/api/v1/replacement/regenerate/${jobId}`, {
      method: "POST",
      body: JSON.stringify({ user_instructions: userInstructions }),
    });
  }

  async getIntegrationStatuses(): Promise<IntegrationsOverviewDTO> {
    return this.request<IntegrationsOverviewDTO>("/api/v1/integrations/status");
  }

  async validateIntegration(integrationId: string): Promise<IntegrationValidationResultDTO> {
    return this.request<IntegrationValidationResultDTO>(`/api/v1/integrations/${integrationId}/validate`, {
      method: "POST",
    });
  }

  async validateAllIntegrations(): Promise<IntegrationValidationResultDTO[]> {
    return this.request<IntegrationValidationResultDTO[]>("/api/v1/integrations/validate-all", {
      method: "POST",
    });
  }

  async exportToCanva(
    projectId: string,
    reportId?: string,
    designType = "presentation"
  ): Promise<CanvaExportResponseDTO> {
    return this.request<CanvaExportResponseDTO>("/api/v1/integrations/canva/export", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, report_id: reportId, design_type: designType }),
    });
  }
}

export interface IntegrationItemDTO {
  id: string;
  name: string;
  category: string;
  provider: string;
  is_configured: boolean;
  status: "ready" | "configured" | "unconfigured" | "degraded" | "error";
  status_message: string;
  required_env_vars: string[];
  optional_env_vars: string[];
  active_model_or_engine?: string;
  capabilities: string[];
  fallback_available: boolean;
  fallback_description?: string;
  error_details?: string;
  last_checked_at: string;
}

export interface IntegrationValidationResultDTO {
  integration_id: string;
  name: string;
  is_valid: boolean;
  status: "ready" | "configured" | "unconfigured" | "degraded" | "error";
  message: string;
  error?: string;
  remediation?: string;
  can_continue_with_arm: boolean;
  fallback_active: boolean;
  checked_at: string;
}

export interface IntegrationsOverviewDTO {
  total_integrations: number;
  configured_count: number;
  unconfigured_count: number;
  all_critical_operational: boolean;
  integrations: IntegrationItemDTO[];
}

export interface CanvaExportResponseDTO {
  status: "success" | "failed" | "unconfigured";
  message: string;
  export_url?: string;
  error?: string;
  remediation?: string;
}



export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";
export type VerificationStatus = "READY" | "PARTIALLY_VERIFIED" | "MISSING_INFORMATION" | "RESEARCH_REQUIRED";

export interface SectionPlanItemDTO {
  section_id: string;
  title: string;
  level: number;
  order: number;
  semantic_role: string;
  purpose: string;
  required: boolean;
  content_requirements: string[];
  project_fact_references: string[];
  evidence_references: string[];
  required_evidence_types: string[];
  research_required: boolean;
  research_notes?: string;
  missing_information: string[];
  generation_notes?: string;
  confidence: ConfidenceLevel;
  verification_status: VerificationStatus;
}

export interface PlanSummaryMetricsDTO {
  total_sections: number;
  ready_sections: number;
  partially_verified_sections: number;
  missing_info_sections: number;
  research_required_sections: number;
  total_missing_items: number;
  total_evidence_mappings: number;
  overall_confidence: ConfidenceLevel;
}

export interface ReportPlanDTO {
  schema_version: string;
  plan_id?: string;
  project_id: string;
  template_id: string;
  template_schema_version: string;
  title: string;
  target_page_count: number;
  sections: SectionPlanItemDTO[];
  global_requirements: string[];
  unresolved_items: string[];
  warnings: string[];
  summary_metrics: PlanSummaryMetricsDTO;
  planner_metadata: {
    planner_version: string;
    ai_provider: string;
    ai_model: string;
    generated_at: string;
    template_schema_version: string;
    project_updated_at?: string;
    evidence_count: number;
    members_count: number;
  };
  is_stale: boolean;
  is_approved: boolean;
  approved_at?: string;
  approved_by?: string;
}

export type BlockType = "heading" | "paragraph" | "bullet_list" | "numbered_list" | "table" | "quote" | "note";
export type GroundingStatus = "grounded" | "partially_grounded" | "requires_review" | "missing_information" | "validation_failed";

export interface ContentBlockDTO {
  block_type: BlockType;
  text: string;
  level?: number;
  items?: string[];
  headers?: string[];
  rows?: string[][];
  source_evidence_ids: string[];
}

export interface MissingInformationDTO {
  field: string;
  reason: string;
  severity: "info" | "warning" | "critical";
}

export interface VisualRequirementDTO {
  visual_type: string;
  description: string;
  status: string;
}

export interface SectionGenerationOutputDTO {
  section_id: string;
  section_title: string;
  section_order: number;
  content_blocks: ContentBlockDTO[];
  missing_information: MissingInformationDTO[];
  grounding_status: GroundingStatus;
  grounding_notes: string[];
  warnings: string[];
  research_marker_preserved: boolean;
  visual_requirements: VisualRequirementDTO[];
  word_count: number;
}

export interface GeneratedReportDTO {
  report_id: string;
  project_id: string;
  template_id: string;
  template_schema_version: string;
  report_plan_id: string;
  report_plan_version: string;
  version_number: number;
  title: string;
  sections: SectionGenerationOutputDTO[];
  overall_grounding: GroundingStatus;
  total_word_count: number;
  status: string;
  metadata: {
    generator_version: string;
    ai_provider: string;
    ai_model: string;
    generated_at: string;
    template_schema_version: string;
    report_plan_id: string;
    report_plan_version: string;
    total_sections_planned: number;
    total_sections_generated: number;
    total_word_count: number;
    generation_job_id?: string;
  };
  created_at: string;
}

export const apiClient = new ReportForgeClient();

export type ClaimType =
  | "project_fact"
  | "project_result"
  | "metric"
  | "technology"
  | "dataset"
  | "methodology"
  | "external_fact"
  | "research_claim"
  | "citation_claim"
  | "inferred_claim";

export type ClaimVerificationStatus =
  | "pending"
  | "supported"
  | "partially_supported"
  | "unsupported"
  | "requires_review"
  | "missing_evidence"
  | "citation_required"
  | "citation_invalid"
  | "verification_failed";

export interface ClaimVerificationRecordDTO {
  verification_id: string;
  report_version_id: string;
  section_id: string;
  claim_id: string;
  text: string;
  claim_type: ClaimType;
  status: ClaimVerificationStatus;
  evidence_ids: string[];
  source_ids: string[];
  reason?: string;
  requires_review: boolean;
  provenance?: any;
  verifier_version: string;
  verified_at: string;
}

export interface VerificationSummaryDTO {
  total_claims: number;
  supported: number;
  partially_supported: number;
  unsupported: number;
  requires_review: number;
  missing_evidence: number;
  citation_required: number;
  citation_invalid: number;
  verification_failed: number;
  grounding_rate_percent: number;
}

export interface QualityGateResultDTO {
  can_proceed_to_document_generation: boolean;
  blocking_issues: string[];
  warnings: string[];
}

export interface ReportVerificationReportDTO {
  id: string;
  report_id: string;
  report_version_id: string;
  version_number: number;
  project_id: string;
  verifier_version: string;
  summary: VerificationSummaryDTO;
  quality_gates: QualityGateResultDTO;
  claims: ClaimVerificationRecordDTO[];
  section_verifications: Record<string, ClaimVerificationRecordDTO[]>;
  status: string;
  verified_at: string;
}

// Stage 11 Types & DTOs
export type CheckStatus = "PASS" | "WARNING" | "FAIL" | "NOT_TESTED";
export type IssueSeverity = "INFO" | "WARNING" | "ERROR" | "BLOCKING";
export type QualityGateStatus = "READY" | "READY_WITH_WARNINGS" | "REVIEW_REQUIRED" | "BLOCKED" | "FAILED";

export interface ValidationCheckDTO {
  check_id: string;
  category: string;
  status: CheckStatus;
  severity: IssueSeverity;
  message: string;
  source?: string;
  section_id?: string;
}

export interface ValidationIssueDTO {
  issue_id: string;
  category: string;
  severity: IssueSeverity;
  message: string;
  section_id?: string;
  section_title?: string;
  affected_claim?: string;
  evidence_id?: string;
  suggested_action?: string;
}

export interface ReportValidationSummaryDTO {
  total_checks: number;
  passed_checks: number;
  warning_checks: number;
  failed_checks: number;
  not_tested_checks: number;
  blocking_count: number;
  errors_count: number;
  warnings_count: number;
  info_count: number;
  gate_status: QualityGateStatus;
}

export interface ReportQualityResultDTO {
  validation_id: string;
  report_id: string;
  report_version_id: string;
  version_number: number;
  project_id: string;
  validator_version: string;
  status: QualityGateStatus;
  gate_status: QualityGateStatus;
  checks: ValidationCheckDTO[];
  issues: ValidationIssueDTO[];
  summary: ReportValidationSummaryDTO;
  is_stale: boolean;
  created_at: string;
}

export interface AIReportAgentInputDTO {
  project_title: string;
  project_description: string;
  user_instructions?: string;
  template_id?: string;
  template_fields?: TemplateFieldDTO[];
  evidence_files?: any[];
  project_id?: string;
  student_name?: string;
  roll_number?: string;
  department?: string;
  guide_name?: string;
}

export interface FieldValidationResult {
  field_name: string;
  is_valid: boolean;
  field_type: string;
  word_count?: number;
  item_count?: number;
  message?: string;
}

export interface ValidationReportDTO {
  is_valid: boolean;
  total_fields: number;
  valid_fields_count: number;
  missing_required_fields: string[];
  field_results: FieldValidationResult[];
  warnings: string[];
}

export interface AIReportAgentOutputDTO {
  status: string;
  stage: string;
  content: Record<string, any>;
  validation: ValidationReportDTO;
  model_used: string;
  generated_at: string;
  job_id?: string;
  error?: string;
}

export interface AgentJobStatusDTO {
  job_id: string;
  status: string;
  stage: string;
  progress_percent: number;
  stage_label: string;
  stage_detail: string;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface ImageRequirementDTO {
  template_field: string;
  section_key: string;
  field_label: string;
  asset_type: string;
  title: string;
  description: string;
  suggested_prompt: string;
  target_dimensions: {
    width?: number;
    height?: number;
    dpi?: number;
    aspect_ratio?: string;
    [key: string]: any;
  };
  acquisition_mode: string;
  license_type: string;
  attribution: string;
}

export interface DetermineImageRequirementsResponseDTO {
  project_title: string;
  total_image_fields: number;
  requirements: ImageRequirementDTO[];
}

export interface ReportAssetItemDTO {
  id: string;
  project_id: string;
  report_id?: string;
  user_id?: string;
  template_field: string;
  asset_type: string;
  source: string;
  title: string;
  caption?: string;
  description?: string;
  file_name: string;
  storage_path: string;
  file_url?: string;
  mime_type: string;
  file_size_bytes: number;
  attribution: string;
  license_info: string;
  section_key?: string;
  metadata?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface PipelineStepResultDTO {
  template_field: string;
  status: string;
  asset?: ReportAssetItemDTO;
  error?: string;
}

export interface AutomaticImagePipelineResponseDTO {
  project_id: string;
  status: string;
  total_images_processed: number;
  successful_images_count: number;
  failed_images_count: number;
  assets: ReportAssetItemDTO[];
  field_mapping: Record<string, string>;
  step_results: PipelineStepResultDTO[];
  completed_at: string;
}

export type ReplacementState =
  | "QUEUED"
  | "ANALYZING"
  | "GENERATING"
  | "REPLACING"
  | "VALIDATING"
  | "COMPLETED"
  | "FAILED";

export interface FieldReplacementAuditDTO {
  field_name: string;
  placeholder: string;
  field_type: string;
  replaced: boolean;
  original_snippet?: string;
  new_snippet?: string;
  formatting_preserved: boolean;
  error?: string;
}

export interface ReplacementErrorDetailDTO {
  field: string;
  reason: string;
}

export interface ReplacementExecutionRequestDTO {
  project_id?: string;
  template_id?: string;
  custom_content?: Record<string, any>;
  custom_assets?: Record<string, any>;
  project_data?: Record<string, any>;
  user_instructions?: string;
  search_query?: string;
  query?: string;
}

export interface ReplacementStatsDTO {
  page_count?: number;
  estimated_word_count?: number;
  paragraphs_count?: number;
  tables_count?: number;
  images_count?: number;
  sections_count?: number;
  generated_sections?: string[];
  unresolved_placeholders?: string[];
  validation_status?: "VALID" | "WARNING" | "INVALID";
}

export interface ReplacementJobResponseDTO {
  job_id: string;
  project_id?: string;
  template_id?: string;
  state: ReplacementState;
  approval_status?: "pending" | "approved";
  approved_at?: string | null;
  progress_percent: number;
  arm_ui_state: "thinking" | "creating" | "completed";
  status_message: string;
  fields_replaced: number;
  total_fields: number;
  images_replaced: number;
  docx_path?: string;
  pdf_path?: string;
  preview_html?: string;
  stats?: ReplacementStatsDTO;
  download_docx_url?: string;
  download_pdf_url?: string;
  preview_url?: string;
  audit: FieldReplacementAuditDTO[];
  errors: ReplacementErrorDetailDTO[];
  warnings: string[];
  created_at: string;
  updated_at: string;
}

export interface ReplacementPreviewResponseDTO {
  job_id: string;
  state: string;
  approval_status?: "pending" | "approved";
  approved_at?: string | null;
  preview_html: string;
  stats?: ReplacementStatsDTO;
  fields_replaced: number;
  total_fields: number;
  images_replaced?: number;
  download_docx_url?: string;
  download_pdf_url?: string;
  warnings: string[];
  errors: ReplacementErrorDetailDTO[];
}


