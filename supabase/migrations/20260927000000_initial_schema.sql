-- ==============================================================================
-- REPORTFORGE AI - Production Database Migration
-- Version: 20260927000000_initial_schema
-- Description: Core entities, RLS policies, indexes, and triggers
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- 1. Profiles Table (Linked to Supabase auth.users)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    institution_name TEXT,
    department TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- 2. Projects Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    project_type TEXT NOT NULL CHECK (project_type IN ('capstone', 'seminar', 'internship', 'weekly_lab', 'thesis', 'research_paper')),
    academic_year TEXT,
    guide_name TEXT,
    abstract_summary TEXT,
    tech_stack TEXT[] DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'analyzing', 'in_progress', 'ready', 'archived')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- 3. Templates Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    original_docx_url TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    is_institution_preset BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- 4. Template Analysis Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS template_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    normalized_schema JSONB NOT NULL,
    detected_sections JSONB NOT NULL,
    typography_rules JSONB NOT NULL,
    page_geometry JSONB NOT NULL,
    confidence_score NUMERIC(3, 2) NOT NULL DEFAULT 0.00,
    review_status TEXT NOT NULL DEFAULT 'pending_review' CHECK (review_status IN ('pending_review', 'approved', 'rejected')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- 5. Project Files (Evidence Repository)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('screenshot', 'pdf', 'docx', 'code', 'csv', 'diagram', 'txt')),
    storage_path TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    extracted_text TEXT,
    parsed_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- 6. Reports Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    template_id UUID NOT NULL REFERENCES templates(id),
    title TEXT NOT NULL,
    report_type TEXT NOT NULL,
    current_version INT DEFAULT 1 NOT NULL,
    status TEXT NOT NULL DEFAULT 'planning' CHECK (status IN ('planning', 'generating', 'validating', 'compiled', 'error')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- 7. Report Sections Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS report_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    parent_section_id UUID REFERENCES report_sections(id),
    section_key TEXT NOT NULL,
    title TEXT NOT NULL,
    sequence_order INT NOT NULL,
    section_level INT NOT NULL DEFAULT 1,
    content_markdown TEXT,
    word_count INT DEFAULT 0,
    evidence_ids UUID[] DEFAULT '{}',
    validation_status TEXT DEFAULT 'pending' CHECK (validation_status IN ('pending', 'valid', 'needs_review', 'error')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- 8. Citations Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    citation_key TEXT NOT NULL,
    title TEXT NOT NULL,
    authors TEXT[] NOT NULL DEFAULT '{}',
    publication TEXT,
    year INT,
    url TEXT,
    doi TEXT,
    verification_status TEXT DEFAULT 'unverified' CHECK (verification_status IN ('verified', 'unverified', 'manual_entry')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- 9. Report Versions Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS report_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    docx_storage_path TEXT,
    pdf_storage_path TEXT,
    validation_summary JSONB DEFAULT '{}',
    compiled_by UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- 10. Generation Jobs Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS generation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL CHECK (job_type IN ('template_analysis', 'plan_generation', 'section_generation', 'document_compilation', 'pdf_conversion')),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
    progress_percentage INT DEFAULT 0,
    error_message TEXT,
    result_payload JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- 11. Weekly Reports Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weekly_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    week_number INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    tasks_planned TEXT NOT NULL,
    tasks_completed TEXT NOT NULL,
    challenges_faced TEXT,
    next_week_goals TEXT,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- 12. Audit Logs Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id),
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id UUID,
    metadata JSONB DEFAULT '{}',
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- -----------------------------------------------------------------------------
-- Indexes for High-Performance Queries
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_templates_owner ON templates(owner_id);
CREATE INDEX IF NOT EXISTS idx_project_files_project ON project_files(project_id);
CREATE INDEX IF NOT EXISTS idx_reports_project ON reports(project_id);
CREATE INDEX IF NOT EXISTS idx_report_sections_report ON report_sections(report_id, sequence_order);
CREATE INDEX IF NOT EXISTS idx_citations_report ON citations(report_id);
CREATE INDEX IF NOT EXISTS idx_jobs_report ON generation_jobs(report_id, status);
CREATE INDEX IF NOT EXISTS idx_weekly_reports_project ON weekly_reports(project_id, week_number);

-- -----------------------------------------------------------------------------
-- Row Level Security (RLS)
-- -----------------------------------------------------------------------------
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE generation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Profiles: users read and update their own profile
CREATE POLICY "Users can manage own profile" ON profiles
    FOR ALL USING (auth.uid() = id);

-- Projects: users manage their own projects
CREATE POLICY "Users can manage own projects" ON projects
    FOR ALL USING (auth.uid() = owner_id);

-- Templates: users see own or presets
CREATE POLICY "Users can manage own templates" ON templates
    FOR ALL USING (auth.uid() = owner_id OR is_institution_preset = TRUE);

-- Template Analysis: users access analysis of accessible templates
CREATE POLICY "Users can view accessible template analysis" ON template_analysis
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM templates
            WHERE templates.id = template_analysis.template_id
            AND (templates.owner_id = auth.uid() OR templates.is_institution_preset = TRUE)
        )
    );

-- Project Files: users manage files for their own projects
CREATE POLICY "Users can manage project files" ON project_files
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projects
            WHERE projects.id = project_files.project_id
            AND projects.owner_id = auth.uid()
        )
    );

-- Reports: users manage their own reports
CREATE POLICY "Users can manage reports" ON reports
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projects
            WHERE projects.id = reports.project_id
            AND projects.owner_id = auth.uid()
        )
    );

-- Report Sections: users manage report sections for their reports
CREATE POLICY "Users can manage report sections" ON report_sections
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM reports
            JOIN projects ON projects.id = reports.project_id
            WHERE reports.id = report_sections.report_id
            AND projects.owner_id = auth.uid()
        )
    );

-- Citations: users manage citations for their reports
CREATE POLICY "Users can manage citations" ON citations
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM reports
            JOIN projects ON projects.id = reports.project_id
            WHERE reports.id = citations.report_id
            AND projects.owner_id = auth.uid()
        )
    );

-- Report Versions: users view versions of their reports
CREATE POLICY "Users can view report versions" ON report_versions
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM reports
            JOIN projects ON projects.id = reports.project_id
            WHERE reports.id = report_versions.report_id
            AND projects.owner_id = auth.uid()
        )
    );

-- Generation Jobs: users see their own jobs
CREATE POLICY "Users can view generation jobs" ON generation_jobs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM reports
            JOIN projects ON projects.id = reports.project_id
            WHERE reports.id = generation_jobs.report_id
            AND projects.owner_id = auth.uid()
        )
    );

-- Weekly Reports: users manage their weekly reports
CREATE POLICY "Users can manage weekly reports" ON weekly_reports
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM projects
            WHERE projects.id = weekly_reports.project_id
            AND projects.owner_id = auth.uid()
        )
    );
