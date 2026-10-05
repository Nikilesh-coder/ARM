-- ==============================================================================
-- ARM - Core Database Foundation Migration
-- Version: 20260929000000_core_arm_schema.sql
-- Description: Establishes complete core ARM tables, columns, relationships, and triggers
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- Helper: Updated_At Trigger Function
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- 1. PROFILES Table (Authenticated User Profiles)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Ensure required columns exist
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS full_name TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS institution_name TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS department TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS avatar_url TEXT;

-- Backfill user_id and name for existing rows
UPDATE public.profiles SET user_id = id WHERE user_id IS NULL;
UPDATE public.profiles SET name = full_name WHERE name IS NULL AND full_name IS NOT NULL;
UPDATE public.profiles SET full_name = name WHERE full_name IS NULL AND name IS NOT NULL;

-- Trigger to sync id/user_id and name/full_name on profiles
CREATE OR REPLACE FUNCTION public.sync_profiles_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.id IS NULL AND NEW.user_id IS NOT NULL THEN
        NEW.id := NEW.user_id;
    END IF;
    IF NEW.user_id IS NULL AND NEW.id IS NOT NULL THEN
        NEW.user_id := NEW.id;
    END IF;
    IF NEW.name IS NULL AND NEW.full_name IS NOT NULL THEN
        NEW.name := NEW.full_name;
    END IF;
    IF NEW.full_name IS NULL AND NEW.name IS NOT NULL THEN
        NEW.full_name := NEW.name;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_profiles_columns ON public.profiles;
CREATE TRIGGER trg_sync_profiles_columns
BEFORE INSERT OR UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.sync_profiles_columns();

-- Updated_at trigger for profiles
DROP TRIGGER IF EXISTS trg_profiles_updated_at ON public.profiles;
CREATE TRIGGER trg_profiles_updated_at
BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Keep auth.users signup trigger in sync
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_name TEXT;
BEGIN
    user_name := COALESCE(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', 'Student User');
    INSERT INTO public.profiles (id, user_id, full_name, name)
    VALUES (new.id, new.id, user_name, user_name)
    ON CONFLICT (id) DO UPDATE
    SET user_id = EXCLUDED.user_id,
        name = COALESCE(EXCLUDED.name, profiles.name),
        full_name = COALESCE(EXCLUDED.full_name, profiles.full_name);
    RETURN NEW;
END;
$$;

-- -----------------------------------------------------------------------------
-- 2. PROJECTS Table (Student Projects)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Ensure required columns exist
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS project_name TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS report_title TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS report_type TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS project_type TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS abstract_summary TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS academic_year TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS guide_name TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS tech_stack TEXT[] DEFAULT '{}';
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'draft';

-- Relax check constraints on project_type and status to allow full flexibility
ALTER TABLE public.projects DROP CONSTRAINT IF EXISTS projects_project_type_check;
ALTER TABLE public.projects DROP CONSTRAINT IF EXISTS projects_status_check;

-- Ensure owner_id is nullable if user_id is provided, and vice-versa
ALTER TABLE public.projects ALTER COLUMN owner_id DROP NOT NULL;
ALTER TABLE public.projects ALTER COLUMN title DROP NOT NULL;
ALTER TABLE public.projects ALTER COLUMN project_type DROP NOT NULL;

-- Backfill projects columns
UPDATE public.projects SET user_id = owner_id WHERE user_id IS NULL AND owner_id IS NOT NULL;
UPDATE public.projects SET owner_id = user_id WHERE owner_id IS NULL AND user_id IS NOT NULL;
UPDATE public.projects SET project_name = title WHERE project_name IS NULL AND title IS NOT NULL;
UPDATE public.projects SET title = project_name WHERE title IS NULL AND project_name IS NOT NULL;
UPDATE public.projects SET report_title = COALESCE(project_name, title) WHERE report_title IS NULL;
UPDATE public.projects SET report_type = COALESCE(project_type, 'capstone') WHERE report_type IS NULL;
UPDATE public.projects SET project_type = COALESCE(report_type, 'capstone') WHERE project_type IS NULL;
UPDATE public.projects SET description = abstract_summary WHERE description IS NULL AND abstract_summary IS NOT NULL;
UPDATE public.projects SET abstract_summary = description WHERE abstract_summary IS NULL AND description IS NOT NULL;

-- Trigger to sync user_id/owner_id and titles on projects
CREATE OR REPLACE FUNCTION public.sync_projects_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_id IS NULL AND NEW.owner_id IS NOT NULL THEN
        NEW.user_id := NEW.owner_id;
    END IF;
    IF NEW.owner_id IS NULL AND NEW.user_id IS NOT NULL THEN
        NEW.owner_id := NEW.user_id;
    END IF;
    IF NEW.project_name IS NULL AND NEW.title IS NOT NULL THEN
        NEW.project_name := NEW.title;
    END IF;
    IF NEW.title IS NULL AND NEW.project_name IS NOT NULL THEN
        NEW.title := NEW.project_name;
    END IF;
    IF NEW.report_title IS NULL THEN
        NEW.report_title := COALESCE(NEW.project_name, NEW.title, 'Untitled Report');
    END IF;
    IF NEW.report_type IS NULL AND NEW.project_type IS NOT NULL THEN
        NEW.report_type := NEW.project_type;
    END IF;
    IF NEW.project_type IS NULL AND NEW.report_type IS NOT NULL THEN
        NEW.project_type := NEW.report_type;
    END IF;
    IF NEW.description IS NULL AND NEW.abstract_summary IS NOT NULL THEN
        NEW.description := NEW.abstract_summary;
    END IF;
    IF NEW.abstract_summary IS NULL AND NEW.description IS NOT NULL THEN
        NEW.abstract_summary := NEW.description;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_projects_columns ON public.projects;
CREATE TRIGGER trg_sync_projects_columns
BEFORE INSERT OR UPDATE ON public.projects
FOR EACH ROW EXECUTE FUNCTION public.sync_projects_columns();

-- Updated_at trigger for projects
DROP TRIGGER IF EXISTS trg_projects_updated_at ON public.projects;
CREATE TRIGGER trg_projects_updated_at
BEFORE UPDATE ON public.projects
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 3. TEMPLATES Table (Uploaded College Templates)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Ensure required columns exist
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE;
ALTER TABLE public.templates DROP CONSTRAINT IF EXISTS templates_project_id_fkey;
ALTER TABLE public.templates ADD CONSTRAINT templates_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS file_name TEXT;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS storage_path TEXT;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS original_docx_url TEXT;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS file_type TEXT DEFAULT 'docx';
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS file_size BIGINT DEFAULT 0;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT DEFAULT 0;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'uploaded';
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS is_institution_preset BOOLEAN DEFAULT FALSE;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL;

-- Relax NOT NULL on legacy columns
ALTER TABLE public.templates ALTER COLUMN owner_id DROP NOT NULL;
ALTER TABLE public.templates ALTER COLUMN name DROP NOT NULL;
ALTER TABLE public.templates ALTER COLUMN original_docx_url DROP NOT NULL;
ALTER TABLE public.templates ALTER COLUMN file_size_bytes DROP NOT NULL;

-- Backfill templates columns
UPDATE public.templates SET user_id = owner_id WHERE user_id IS NULL AND owner_id IS NOT NULL;
UPDATE public.templates SET owner_id = user_id WHERE owner_id IS NULL AND user_id IS NOT NULL;
UPDATE public.templates SET file_name = name WHERE file_name IS NULL AND name IS NOT NULL;
UPDATE public.templates SET name = file_name WHERE name IS NULL AND file_name IS NOT NULL;
UPDATE public.templates SET storage_path = original_docx_url WHERE storage_path IS NULL AND original_docx_url IS NOT NULL;
UPDATE public.templates SET original_docx_url = storage_path WHERE original_docx_url IS NULL AND storage_path IS NOT NULL;
UPDATE public.templates SET file_size = file_size_bytes WHERE file_size IS NULL AND file_size_bytes IS NOT NULL;
UPDATE public.templates SET file_size_bytes = file_size WHERE file_size_bytes IS NULL AND file_size IS NOT NULL;

-- Trigger to sync template columns
CREATE OR REPLACE FUNCTION public.sync_templates_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_id IS NULL AND NEW.owner_id IS NOT NULL THEN
        NEW.user_id := NEW.owner_id;
    END IF;
    IF NEW.owner_id IS NULL AND NEW.user_id IS NOT NULL THEN
        NEW.owner_id := NEW.user_id;
    END IF;
    IF NEW.file_name IS NULL AND NEW.name IS NOT NULL THEN
        NEW.file_name := NEW.name;
    END IF;
    IF NEW.name IS NULL AND NEW.file_name IS NOT NULL THEN
        NEW.name := NEW.file_name;
    END IF;
    IF NEW.storage_path IS NULL AND NEW.original_docx_url IS NOT NULL THEN
        NEW.storage_path := NEW.original_docx_url;
    END IF;
    IF NEW.original_docx_url IS NULL AND NEW.storage_path IS NOT NULL THEN
        NEW.original_docx_url := NEW.storage_path;
    END IF;
    IF NEW.file_size IS NULL AND NEW.file_size_bytes IS NOT NULL THEN
        NEW.file_size := NEW.file_size_bytes;
    END IF;
    IF NEW.file_size_bytes IS NULL AND NEW.file_size IS NOT NULL THEN
        NEW.file_size_bytes := NEW.file_size;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_templates_columns ON public.templates;
CREATE TRIGGER trg_sync_templates_columns
BEFORE INSERT OR UPDATE ON public.templates
FOR EACH ROW EXECUTE FUNCTION public.sync_templates_columns();

-- Updated_at trigger for templates
DROP TRIGGER IF EXISTS trg_templates_updated_at ON public.templates;
CREATE TRIGGER trg_templates_updated_at
BEFORE UPDATE ON public.templates
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 4. TEMPLATE_ANALYSIS Table (Analyzed Template Structure & JSON)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.template_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES public.templates(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Ensure required columns exist
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS data JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS normalized_schema JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS detected_sections JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS typography_rules JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS page_geometry JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS analysis_status TEXT DEFAULT 'completed';
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'completed';
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS review_status TEXT DEFAULT 'pending_review';
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS warnings JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS confidence JSONB DEFAULT '{"score": 1.0}'::jsonb;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3, 2) DEFAULT 1.00;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL;

-- Relax NOT NULL constraints on legacy columns
ALTER TABLE public.template_analysis ALTER COLUMN normalized_schema DROP NOT NULL;
ALTER TABLE public.template_analysis ALTER COLUMN detected_sections DROP NOT NULL;
ALTER TABLE public.template_analysis ALTER COLUMN typography_rules DROP NOT NULL;
ALTER TABLE public.template_analysis ALTER COLUMN page_geometry DROP NOT NULL;
ALTER TABLE public.template_analysis DROP CONSTRAINT IF EXISTS template_analysis_review_status_check;

-- Backfill data from normalized_schema if data is empty
UPDATE public.template_analysis SET data = normalized_schema WHERE (data IS NULL OR data = '{}'::jsonb) AND normalized_schema IS NOT NULL AND normalized_schema != '{}'::jsonb;
UPDATE public.template_analysis SET normalized_schema = data WHERE (normalized_schema IS NULL OR normalized_schema = '{}'::jsonb) AND data IS NOT NULL AND data != '{}'::jsonb;

-- Trigger to sync data / normalized_schema
CREATE OR REPLACE FUNCTION public.sync_template_analysis_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF (NEW.data IS NULL OR NEW.data = '{}'::jsonb) AND NEW.normalized_schema IS NOT NULL THEN
        NEW.data := NEW.normalized_schema;
    END IF;
    IF (NEW.normalized_schema IS NULL OR NEW.normalized_schema = '{}'::jsonb) AND NEW.data IS NOT NULL THEN
        NEW.normalized_schema := NEW.data;
    END IF;
    IF NEW.analysis_status IS NULL AND NEW.status IS NOT NULL THEN
        NEW.analysis_status := NEW.status;
    END IF;
    IF NEW.status IS NULL AND NEW.analysis_status IS NOT NULL THEN
        NEW.status := NEW.analysis_status;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_template_analysis_columns ON public.template_analysis;
CREATE TRIGGER trg_sync_template_analysis_columns
BEFORE INSERT OR UPDATE ON public.template_analysis
FOR EACH ROW EXECUTE FUNCTION public.sync_template_analysis_columns();

-- Updated_at trigger for template_analysis
DROP TRIGGER IF EXISTS trg_template_analysis_updated_at ON public.template_analysis;
CREATE TRIGGER trg_template_analysis_updated_at
BEFORE UPDATE ON public.template_analysis
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 5. PROJECT_FILES Table (Evidence Metadata Repository)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.project_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Ensure required columns exist
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS file_name TEXT;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS storage_path TEXT;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS file_type TEXT DEFAULT 'general';
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'general';
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS file_size BIGINT DEFAULT 0;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT DEFAULT 0;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS extraction_status TEXT DEFAULT 'pending';
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS extracted_text TEXT;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS parsed_metadata JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL;

-- Relax legacy check constraints
ALTER TABLE public.project_files DROP CONSTRAINT IF EXISTS project_files_file_type_check;
ALTER TABLE public.project_files ALTER COLUMN file_size_bytes DROP NOT NULL;

-- Trigger to sync file_size / file_size_bytes
CREATE OR REPLACE FUNCTION public.sync_project_files_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.file_size IS NULL AND NEW.file_size_bytes IS NOT NULL THEN
        NEW.file_size := NEW.file_size_bytes;
    END IF;
    IF NEW.file_size_bytes IS NULL AND NEW.file_size IS NOT NULL THEN
        NEW.file_size_bytes := NEW.file_size;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_project_files_columns ON public.project_files;
CREATE TRIGGER trg_sync_project_files_columns
BEFORE INSERT OR UPDATE ON public.project_files
FOR EACH ROW EXECUTE FUNCTION public.sync_project_files_columns();

-- Updated_at trigger for project_files
DROP TRIGGER IF EXISTS trg_project_files_updated_at ON public.project_files;
CREATE TRIGGER trg_project_files_updated_at
BEFORE UPDATE ON public.project_files
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 6. REPORTS Table (Generated Report Information)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Ensure required columns exist
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS template_id UUID REFERENCES public.templates(id) ON DELETE SET NULL;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS title TEXT DEFAULT 'Academic Report';
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS report_type TEXT DEFAULT 'capstone';
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS current_version INT DEFAULT 1;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'planning';
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS docx_storage_path TEXT;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS pdf_storage_path TEXT;

-- Relax legacy check and nullability constraints
ALTER TABLE public.reports DROP CONSTRAINT IF EXISTS reports_status_check;
ALTER TABLE public.reports ALTER COLUMN template_id DROP NOT NULL;
ALTER TABLE public.reports ALTER COLUMN title DROP NOT NULL;
ALTER TABLE public.reports ALTER COLUMN report_type DROP NOT NULL;

-- Updated_at trigger for reports
DROP TRIGGER IF EXISTS trg_reports_updated_at ON public.reports;
CREATE TRIGGER trg_reports_updated_at
BEFORE UPDATE ON public.reports
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 7. GENERATION_JOBS Table (Long-Running ARM Generation Jobs)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.generation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Ensure required columns exist
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS report_id UUID REFERENCES public.reports(id) ON DELETE CASCADE;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS job_type TEXT DEFAULT 'report_generation';
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'queued';
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS progress INT DEFAULT 0;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS progress_percentage INT DEFAULT 0;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS current_stage TEXT DEFAULT 'queued';
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS result_payload JSONB DEFAULT '{}'::jsonb;

-- Relax report_id NOT NULL so jobs can queue before report record is minted
ALTER TABLE public.generation_jobs ALTER COLUMN report_id DROP NOT NULL;

-- Replace status check constraint to include 'running', 'queued', 'completed', 'failed', 'cancelled'
ALTER TABLE public.generation_jobs DROP CONSTRAINT IF EXISTS generation_jobs_status_check;
ALTER TABLE public.generation_jobs ADD CONSTRAINT generation_jobs_status_check 
    CHECK (status IN ('queued', 'running', 'processing', 'completed', 'failed', 'cancelled'));

-- Drop restrictive job_type check if present
ALTER TABLE public.generation_jobs DROP CONSTRAINT IF EXISTS generation_jobs_job_type_check;

-- Trigger to sync progress and progress_percentage
CREATE OR REPLACE FUNCTION public.sync_generation_jobs_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.progress IS NULL AND NEW.progress_percentage IS NOT NULL THEN
        NEW.progress := NEW.progress_percentage;
    END IF;
    IF NEW.progress_percentage IS NULL AND NEW.progress IS NOT NULL THEN
        NEW.progress_percentage := NEW.progress;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_generation_jobs_columns ON public.generation_jobs;
CREATE TRIGGER trg_sync_generation_jobs_columns
BEFORE INSERT OR UPDATE ON public.generation_jobs
FOR EACH ROW EXECUTE FUNCTION public.sync_generation_jobs_columns();

-- Updated_at trigger for generation_jobs
DROP TRIGGER IF EXISTS trg_generation_jobs_updated_at ON public.generation_jobs;
CREATE TRIGGER trg_generation_jobs_updated_at
BEFORE UPDATE ON public.generation_jobs
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- High-Performance Indexes for Foreign Keys & Ownership Lookups
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON public.profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON public.projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON public.projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_templates_project_id ON public.templates(project_id);
CREATE INDEX IF NOT EXISTS idx_templates_user_id ON public.templates(user_id);
CREATE INDEX IF NOT EXISTS idx_template_analysis_template_id ON public.template_analysis(template_id);
CREATE INDEX IF NOT EXISTS idx_project_files_project_id ON public.project_files(project_id);
CREATE INDEX IF NOT EXISTS idx_project_files_user_id ON public.project_files(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_project_id ON public.reports(project_id);
CREATE INDEX IF NOT EXISTS idx_reports_user_id ON public.reports(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_template_id ON public.reports(template_id);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_project_id ON public.generation_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_user_id ON public.generation_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_report_id ON public.generation_jobs(report_id);
