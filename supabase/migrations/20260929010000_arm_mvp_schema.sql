-- ==============================================================================
-- ARM (AI Academic Report Assistant) - Core Database Foundation Migration
-- Version: 20260929010000_arm_mvp_schema.sql
-- Description: Establishes full production-ready MVP schema, foreign keys,
--              report_versions table, RLS policies, validation checks, and indexes.
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
-- 1. PROFILES Table (User Accounts)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,
    role TEXT NOT NULL DEFAULT 'student',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Ensure required columns exist on profiles
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS full_name TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'student';
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS institution_name TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS department TEXT;

-- Role constraint
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS chk_profiles_role;
ALTER TABLE public.profiles ADD CONSTRAINT chk_profiles_role CHECK (role IN ('student', 'admin'));

-- Backfill profile email from auth.users if available
DO $$
BEGIN
    UPDATE public.profiles p
    SET email = u.email
    FROM auth.users u
    WHERE p.id = u.id AND (p.email IS NULL OR p.email = '');
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

-- Backfill profile user_id and names
UPDATE public.profiles SET user_id = id WHERE user_id IS NULL;
UPDATE public.profiles SET name = full_name WHERE name IS NULL AND full_name IS NOT NULL;
UPDATE public.profiles SET full_name = name WHERE full_name IS NULL AND name IS NOT NULL;

-- Trigger to sync user_id/id and name/full_name
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

DROP TRIGGER IF EXISTS trg_profiles_updated_at ON public.profiles;
CREATE TRIGGER trg_profiles_updated_at
BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Trigger to auto-create profile on auth.users sign up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_name TEXT;
BEGIN
    user_name := COALESCE(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', split_part(new.email, '@', 1));
    INSERT INTO public.profiles (id, user_id, email, full_name, name, role)
    VALUES (new.id, new.id, new.email, user_name, user_name, 'student')
    ON CONFLICT (id) DO UPDATE
    SET email = COALESCE(EXCLUDED.email, profiles.email),
        name = COALESCE(EXCLUDED.name, profiles.name),
        full_name = COALESCE(EXCLUDED.full_name, profiles.full_name);
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- -----------------------------------------------------------------------------
-- 2. PROJECTS Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Ensure all required columns exist
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS project_name TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS report_title TEXT;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS report_type TEXT DEFAULT 'major_project';
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'draft';
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS target_page_count INTEGER DEFAULT 30;

-- Sync user_id/owner_id and title/project_name
UPDATE public.projects SET user_id = owner_id WHERE user_id IS NULL AND owner_id IS NOT NULL;
UPDATE public.projects SET owner_id = user_id WHERE owner_id IS NULL AND user_id IS NOT NULL;
UPDATE public.projects SET title = project_name WHERE (title IS NULL OR title = '') AND project_name IS NOT NULL;
UPDATE public.projects SET project_name = title WHERE (project_name IS NULL OR project_name = '') AND title IS NOT NULL;
UPDATE public.projects SET report_title = title WHERE (report_title IS NULL OR report_title = '') AND title IS NOT NULL;

UPDATE public.projects SET title = 'Academic Report Project' WHERE title IS NULL;
ALTER TABLE public.projects ALTER COLUMN title SET NOT NULL;

-- Default null or legacy statuses
UPDATE public.projects SET status = 'active' WHERE status = 'ready';
UPDATE public.projects SET status = 'draft' WHERE status IS NULL OR status NOT IN ('draft', 'active', 'generating', 'completed', 'archived');

-- Project status check constraint
ALTER TABLE public.projects DROP CONSTRAINT IF EXISTS chk_projects_status;
ALTER TABLE public.projects ADD CONSTRAINT chk_projects_status 
    CHECK (status IN ('draft', 'active', 'generating', 'completed', 'archived'));

-- Project sync triggers
CREATE OR REPLACE FUNCTION public.sync_projects_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_id IS NULL AND NEW.owner_id IS NOT NULL THEN
        NEW.user_id := NEW.owner_id;
    END IF;
    IF NEW.owner_id IS NULL AND NEW.user_id IS NOT NULL THEN
        NEW.owner_id := NEW.user_id;
    END IF;
    IF NEW.title IS NULL AND NEW.project_name IS NOT NULL THEN
        NEW.title := NEW.project_name;
    END IF;
    IF NEW.project_name IS NULL AND NEW.title IS NOT NULL THEN
        NEW.project_name := NEW.title;
    END IF;
    IF NEW.report_title IS NULL AND NEW.title IS NOT NULL THEN
        NEW.report_title := NEW.title;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_projects_columns ON public.projects;
CREATE TRIGGER trg_sync_projects_columns
BEFORE INSERT OR UPDATE ON public.projects
FOR EACH ROW EXECUTE FUNCTION public.sync_projects_columns();

DROP TRIGGER IF EXISTS trg_projects_updated_at ON public.projects;
CREATE TRIGGER trg_projects_updated_at
BEFORE UPDATE ON public.projects
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 3. TEMPLATES Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    original_file_path TEXT NOT NULL,
    file_type TEXT DEFAULT 'docx',
    file_size BIGINT,
    status TEXT NOT NULL DEFAULT 'uploaded',
    analysis_status TEXT DEFAULT 'pending',
    is_locked BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS file_name TEXT;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS original_file_path TEXT;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS storage_path TEXT;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS file_type TEXT DEFAULT 'docx';
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS file_size BIGINT;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'uploaded';
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS analysis_status TEXT DEFAULT 'pending';
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT false;

-- Sync template fields
UPDATE public.templates SET name = file_name WHERE (name IS NULL OR name = '') AND file_name IS NOT NULL;
UPDATE public.templates SET file_name = name WHERE (file_name IS NULL OR file_name = '') AND name IS NOT NULL;
UPDATE public.templates SET original_file_path = storage_path WHERE (original_file_path IS NULL OR original_file_path = '') AND storage_path IS NOT NULL;
UPDATE public.templates SET storage_path = original_file_path WHERE (storage_path IS NULL OR storage_path = '') AND original_file_path IS NOT NULL;

-- Default fallback values
UPDATE public.templates SET name = 'Default Template' WHERE name IS NULL;
UPDATE public.templates SET original_file_path = 'templates/default.docx' WHERE original_file_path IS NULL;
UPDATE public.templates SET status = 'uploaded' WHERE status IS NULL;

ALTER TABLE public.templates ALTER COLUMN name SET NOT NULL;
ALTER TABLE public.templates ALTER COLUMN original_file_path SET NOT NULL;

-- Template status constraint
ALTER TABLE public.templates DROP CONSTRAINT IF EXISTS chk_templates_status;
ALTER TABLE public.templates ADD CONSTRAINT chk_templates_status
    CHECK (status IN ('uploaded', 'analyzing', 'analyzed', 'confirmed', 'failed'));

-- Template sync trigger
CREATE OR REPLACE FUNCTION public.sync_templates_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.name IS NULL AND NEW.file_name IS NOT NULL THEN
        NEW.name := NEW.file_name;
    END IF;
    IF NEW.file_name IS NULL AND NEW.name IS NOT NULL THEN
        NEW.file_name := NEW.name;
    END IF;
    IF NEW.original_file_path IS NULL AND NEW.storage_path IS NOT NULL THEN
        NEW.original_file_path := NEW.storage_path;
    END IF;
    IF NEW.storage_path IS NULL AND NEW.original_file_path IS NOT NULL THEN
        NEW.storage_path := NEW.original_file_path;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_templates_columns ON public.templates;
CREATE TRIGGER trg_sync_templates_columns
BEFORE INSERT OR UPDATE ON public.templates
FOR EACH ROW EXECUTE FUNCTION public.sync_templates_columns();

DROP TRIGGER IF EXISTS trg_templates_updated_at ON public.templates;
CREATE TRIGGER trg_templates_updated_at
BEFORE UPDATE ON public.templates
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 4. TEMPLATE_ANALYSIS Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.template_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL UNIQUE REFERENCES public.templates(id) ON DELETE CASCADE,
    schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence TEXT DEFAULT 'high',
    warnings JSONB DEFAULT '[]'::jsonb,
    parser_version TEXT DEFAULT '1.0',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS template_id UUID REFERENCES public.templates(id) ON DELETE CASCADE;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS schema_json JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS data JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS confidence TEXT DEFAULT 'high';
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS warnings JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS parser_version TEXT DEFAULT '1.0';
ALTER TABLE public.template_analysis ADD COLUMN IF NOT EXISTS analysis_status TEXT DEFAULT 'completed';

-- Sync data and schema_json
UPDATE public.template_analysis SET schema_json = data WHERE (schema_json IS NULL OR schema_json = '{}'::jsonb) AND data IS NOT NULL;
UPDATE public.template_analysis SET data = schema_json WHERE (data IS NULL OR data = '{}'::jsonb) AND schema_json IS NOT NULL;

UPDATE public.template_analysis SET schema_json = '{}'::jsonb WHERE schema_json IS NULL;
ALTER TABLE public.template_analysis ALTER COLUMN schema_json SET NOT NULL;

-- Unique constraint on template_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'template_analysis_template_id_key'
    ) THEN
        ALTER TABLE public.template_analysis ADD CONSTRAINT template_analysis_template_id_key UNIQUE (template_id);
    END IF;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

CREATE OR REPLACE FUNCTION public.sync_template_analysis_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.schema_json IS NULL AND NEW.data IS NOT NULL THEN
        NEW.schema_json := NEW.data;
    END IF;
    IF NEW.data IS NULL AND NEW.schema_json IS NOT NULL THEN
        NEW.data := NEW.schema_json;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_template_analysis_columns ON public.template_analysis;
CREATE TRIGGER trg_sync_template_analysis_columns
BEFORE INSERT OR UPDATE ON public.template_analysis
FOR EACH ROW EXECUTE FUNCTION public.sync_template_analysis_columns();

DROP TRIGGER IF EXISTS trg_template_analysis_updated_at ON public.template_analysis;
CREATE TRIGGER trg_template_analysis_updated_at
BEFORE UPDATE ON public.template_analysis
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 5. PROJECT_FILES Table (Evidence)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.project_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_type TEXT,
    file_size BIGINT,
    category TEXT NOT NULL DEFAULT 'other',
    extraction_status TEXT NOT NULL DEFAULT 'pending',
    extracted_text TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS file_name TEXT;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS storage_path TEXT;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS file_type TEXT;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS file_size BIGINT;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'other';
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS extraction_status TEXT DEFAULT 'pending';
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS extracted_text TEXT;
ALTER TABLE public.project_files ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Categories check constraint
ALTER TABLE public.project_files DROP CONSTRAINT IF EXISTS chk_project_files_category;
ALTER TABLE public.project_files ADD CONSTRAINT chk_project_files_category
    CHECK (category IN (
        'documentation', 'source_code', 'screenshots', 'results',
        'research', 'presentation', 'diagrams', 'previous_report', 'other'
    ));

-- Extraction status check constraint
ALTER TABLE public.project_files DROP CONSTRAINT IF EXISTS chk_project_files_extraction_status;
ALTER TABLE public.project_files ADD CONSTRAINT chk_project_files_extraction_status
    CHECK (extraction_status IN ('pending', 'processing', 'completed', 'failed'));

DROP TRIGGER IF EXISTS trg_project_files_updated_at ON public.project_files;
CREATE TRIGGER trg_project_files_updated_at
BEFORE UPDATE ON public.project_files
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 6. REPORTS Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    template_id UUID NOT NULL REFERENCES public.templates(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    current_version_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS template_id UUID REFERENCES public.templates(id) ON DELETE RESTRICT;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'draft';
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS current_version_id UUID;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS current_version INTEGER DEFAULT 1;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS docx_storage_path TEXT;
ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS pdf_storage_path TEXT;

-- Fallback report titles
UPDATE public.reports SET title = 'Academic Report' WHERE title IS NULL;
ALTER TABLE public.reports ALTER COLUMN title SET NOT NULL;

-- Report status check constraint
ALTER TABLE public.reports DROP CONSTRAINT IF EXISTS chk_reports_status;
ALTER TABLE public.reports ADD CONSTRAINT chk_reports_status
    CHECK (status IN ('draft', 'planning', 'generating', 'validating', 'completed', 'failed'));

DROP TRIGGER IF EXISTS trg_reports_updated_at ON public.reports;
CREATE TRIGGER trg_reports_updated_at
BEFORE UPDATE ON public.reports
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 7. REPORT_VERSIONS Table (Version History)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.report_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES public.reports(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    content_json JSONB DEFAULT '{}'::jsonb,
    validation_json JSONB,
    generation_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_report_version UNIQUE (report_id, version_number)
);

ALTER TABLE public.report_versions ADD COLUMN IF NOT EXISTS content_json JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.report_versions ADD COLUMN IF NOT EXISTS validation_json JSONB;
ALTER TABLE public.report_versions ADD COLUMN IF NOT EXISTS generation_metadata JSONB;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_report_version'
    ) THEN
        ALTER TABLE public.report_versions ADD CONSTRAINT uq_report_version UNIQUE (report_id, version_number);
    END IF;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

-- Foreign key from reports(current_version_id) to report_versions(id)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_reports_current_version_id'
    ) THEN
        ALTER TABLE public.reports
        ADD CONSTRAINT fk_reports_current_version_id
        FOREIGN KEY (current_version_id) REFERENCES public.report_versions(id) ON DELETE SET NULL;
    END IF;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

-- -----------------------------------------------------------------------------
-- 8. GENERATION_JOBS Table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.generation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
    report_id UUID REFERENCES public.reports(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    progress INTEGER NOT NULL DEFAULT 0,
    current_step TEXT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS report_id UUID REFERENCES public.reports(id) ON DELETE CASCADE;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS job_type TEXT;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'queued';
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS current_step TEXT;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS current_stage TEXT;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE public.generation_jobs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Sync current_step and current_stage
CREATE OR REPLACE FUNCTION public.sync_generation_jobs_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.current_step IS NULL AND NEW.current_stage IS NOT NULL THEN
        NEW.current_step := NEW.current_stage;
    END IF;
    IF NEW.current_stage IS NULL AND NEW.current_step IS NOT NULL THEN
        NEW.current_stage := NEW.current_step;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_generation_jobs_columns ON public.generation_jobs;
CREATE TRIGGER trg_sync_generation_jobs_columns
BEFORE INSERT OR UPDATE ON public.generation_jobs
FOR EACH ROW EXECUTE FUNCTION public.sync_generation_jobs_columns();

-- Constraints on generation_jobs
ALTER TABLE public.generation_jobs DROP CONSTRAINT IF EXISTS chk_generation_jobs_type;
ALTER TABLE public.generation_jobs ADD CONSTRAINT chk_generation_jobs_type
    CHECK (job_type IN (
        'template_analysis', 'report_planning', 'content_generation',
        'document_generation', 'validation'
    ));

ALTER TABLE public.generation_jobs DROP CONSTRAINT IF EXISTS chk_generation_jobs_status;
ALTER TABLE public.generation_jobs ADD CONSTRAINT chk_generation_jobs_status
    CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'));

DROP TRIGGER IF EXISTS trg_generation_jobs_updated_at ON public.generation_jobs;
CREATE TRIGGER trg_generation_jobs_updated_at
BEFORE UPDATE ON public.generation_jobs
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 9. PERFORMANCE INDEXES
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON public.projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON public.projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON public.projects(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_templates_user_id ON public.templates(user_id);
CREATE INDEX IF NOT EXISTS idx_templates_project_id ON public.templates(project_id);
CREATE INDEX IF NOT EXISTS idx_templates_status ON public.templates(status);
CREATE INDEX IF NOT EXISTS idx_templates_created_at ON public.templates(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_template_analysis_template_id ON public.template_analysis(template_id);

CREATE INDEX IF NOT EXISTS idx_project_files_project_id ON public.project_files(project_id);
CREATE INDEX IF NOT EXISTS idx_project_files_user_id ON public.project_files(user_id);
CREATE INDEX IF NOT EXISTS idx_project_files_category ON public.project_files(category);
CREATE INDEX IF NOT EXISTS idx_project_files_created_at ON public.project_files(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reports_project_id ON public.reports(project_id);
CREATE INDEX IF NOT EXISTS idx_reports_user_id ON public.reports(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_template_id ON public.reports(template_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON public.reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON public.reports(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_report_versions_report_id ON public.report_versions(report_id);
CREATE INDEX IF NOT EXISTS idx_report_versions_version_number ON public.report_versions(report_id, version_number);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_user_id ON public.generation_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_project_id ON public.generation_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_report_id ON public.generation_jobs(report_id);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_status ON public.generation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_created_at ON public.generation_jobs(created_at DESC);

-- -----------------------------------------------------------------------------
-- 10. ROW LEVEL SECURITY (RLS) POLICIES
-- -----------------------------------------------------------------------------
-- Enable RLS on all 8 tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.template_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generation_jobs ENABLE ROW LEVEL SECURITY;

-- 10.1 Profiles Policies
DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
CREATE POLICY "profiles_select_own" ON public.profiles
    FOR SELECT TO authenticated
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "profiles_insert_own" ON public.profiles;
CREATE POLICY "profiles_insert_own" ON public.profiles
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
CREATE POLICY "profiles_update_own" ON public.profiles
    FOR UPDATE TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- 10.2 Projects Policies
DROP POLICY IF EXISTS "projects_select_own" ON public.projects;
CREATE POLICY "projects_select_own" ON public.projects
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "projects_insert_own" ON public.projects;
CREATE POLICY "projects_insert_own" ON public.projects
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "projects_update_own" ON public.projects;
CREATE POLICY "projects_update_own" ON public.projects
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "projects_delete_own" ON public.projects;
CREATE POLICY "projects_delete_own" ON public.projects
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- 10.3 Templates Policies
DROP POLICY IF EXISTS "templates_select_own" ON public.templates;
CREATE POLICY "templates_select_own" ON public.templates
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "templates_insert_own" ON public.templates;
CREATE POLICY "templates_insert_own" ON public.templates
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "templates_update_own" ON public.templates;
CREATE POLICY "templates_update_own" ON public.templates
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "templates_delete_own" ON public.templates;
CREATE POLICY "templates_delete_own" ON public.templates
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- 10.4 Template Analysis Policies (Owned via templates)
DROP POLICY IF EXISTS "template_analysis_select_own" ON public.template_analysis;
CREATE POLICY "template_analysis_select_own" ON public.template_analysis
    FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.templates t
        WHERE t.id = template_analysis.template_id
          AND t.user_id = auth.uid()
    ));

DROP POLICY IF EXISTS "template_analysis_insert_own" ON public.template_analysis;
CREATE POLICY "template_analysis_insert_own" ON public.template_analysis
    FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.templates t
        WHERE t.id = template_analysis.template_id
          AND t.user_id = auth.uid()
    ));

DROP POLICY IF EXISTS "template_analysis_update_own" ON public.template_analysis;
CREATE POLICY "template_analysis_update_own" ON public.template_analysis
    FOR UPDATE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.templates t
        WHERE t.id = template_analysis.template_id
          AND t.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.templates t
        WHERE t.id = template_analysis.template_id
          AND t.user_id = auth.uid()
    ));

DROP POLICY IF EXISTS "template_analysis_delete_own" ON public.template_analysis;
CREATE POLICY "template_analysis_delete_own" ON public.template_analysis
    FOR DELETE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.templates t
        WHERE t.id = template_analysis.template_id
          AND t.user_id = auth.uid()
    ));

-- 10.5 Project Files Policies
DROP POLICY IF EXISTS "project_files_select_own" ON public.project_files;
CREATE POLICY "project_files_select_own" ON public.project_files
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "project_files_insert_own" ON public.project_files;
CREATE POLICY "project_files_insert_own" ON public.project_files
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "project_files_update_own" ON public.project_files;
CREATE POLICY "project_files_update_own" ON public.project_files
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "project_files_delete_own" ON public.project_files;
CREATE POLICY "project_files_delete_own" ON public.project_files
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- 10.6 Reports Policies
DROP POLICY IF EXISTS "reports_select_own" ON public.reports;
CREATE POLICY "reports_select_own" ON public.reports
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "reports_insert_own" ON public.reports;
CREATE POLICY "reports_insert_own" ON public.reports
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "reports_update_own" ON public.reports;
CREATE POLICY "reports_update_own" ON public.reports
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "reports_delete_own" ON public.reports;
CREATE POLICY "reports_delete_own" ON public.reports
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- 10.7 Report Versions Policies (Owned via reports)
DROP POLICY IF EXISTS "report_versions_select_own" ON public.report_versions;
CREATE POLICY "report_versions_select_own" ON public.report_versions
    FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.reports r
        WHERE r.id = report_versions.report_id
          AND r.user_id = auth.uid()
    ));

DROP POLICY IF EXISTS "report_versions_insert_own" ON public.report_versions;
CREATE POLICY "report_versions_insert_own" ON public.report_versions
    FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.reports r
        WHERE r.id = report_versions.report_id
          AND r.user_id = auth.uid()
    ));

DROP POLICY IF EXISTS "report_versions_update_own" ON public.report_versions;
CREATE POLICY "report_versions_update_own" ON public.report_versions
    FOR UPDATE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.reports r
        WHERE r.id = report_versions.report_id
          AND r.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.reports r
        WHERE r.id = report_versions.report_id
          AND r.user_id = auth.uid()
    ));

DROP POLICY IF EXISTS "report_versions_delete_own" ON public.report_versions;
CREATE POLICY "report_versions_delete_own" ON public.report_versions
    FOR DELETE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.reports r
        WHERE r.id = report_versions.report_id
          AND r.user_id = auth.uid()
    ));

-- 10.8 Generation Jobs Policies
DROP POLICY IF EXISTS "generation_jobs_select_own" ON public.generation_jobs;
CREATE POLICY "generation_jobs_select_own" ON public.generation_jobs
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "generation_jobs_insert_own" ON public.generation_jobs;
CREATE POLICY "generation_jobs_insert_own" ON public.generation_jobs
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "generation_jobs_update_own" ON public.generation_jobs;
CREATE POLICY "generation_jobs_update_own" ON public.generation_jobs
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "generation_jobs_delete_own" ON public.generation_jobs;
CREATE POLICY "generation_jobs_delete_own" ON public.generation_jobs
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- -----------------------------------------------------------------------------
-- 11. EXPLICIT FOREIGN KEYS & DEFAULT CONSTRAINTS
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_projects_user_id') THEN
        ALTER TABLE public.projects ADD CONSTRAINT fk_projects_user_id FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_templates_user_id') THEN
        ALTER TABLE public.templates ADD CONSTRAINT fk_templates_user_id FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_project_files_user_id') THEN
        ALTER TABLE public.project_files ADD CONSTRAINT fk_project_files_user_id FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_reports_user_id') THEN
        ALTER TABLE public.reports ADD CONSTRAINT fk_reports_user_id FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_generation_jobs_user_id') THEN
        ALTER TABLE public.generation_jobs ADD CONSTRAINT fk_generation_jobs_user_id FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;
    END IF;
END $$;

ALTER TABLE public.project_files ALTER COLUMN file_type SET DEFAULT 'document';
ALTER TABLE public.project_files ALTER COLUMN category SET DEFAULT 'other';
