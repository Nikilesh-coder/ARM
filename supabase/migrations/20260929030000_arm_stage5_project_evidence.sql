-- ==============================================================================
-- ARM Stage 5 Migration: Project Information + Evidence Locker
-- Adds academic fields to projects, metadata to project_files (evidence),
-- and creates project_members table with RLS and cascade rules.
-- Preserves all Stages 1-4 structures without breaking changes.
-- ==============================================================================

-- 1. Extend projects table with structured academic fields
ALTER TABLE public.projects
    ADD COLUMN IF NOT EXISTS problem_statement TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS objectives TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS scope TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS methodology TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS expected_outcome TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS actual_outcome TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS start_date TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS end_date TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS department TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS institution TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS semester TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS additional_notes TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS is_team_project BOOLEAN DEFAULT FALSE;

-- 2. Extend project_files table for Evidence Locker integrity & categorization
ALTER TABLE public.project_files
    ADD COLUMN IF NOT EXISTS mime_type TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS sha256_hash TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS description TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS upload_status TEXT DEFAULT 'ready',
    ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'ready',
    ADD COLUMN IF NOT EXISTS processing_error TEXT DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_project_files_category ON public.project_files(category);
CREATE INDEX IF NOT EXISTS idx_project_files_sha256 ON public.project_files(sha256_hash);

-- Update project_files category constraint to include all Stage 5 evidence categories
ALTER TABLE public.project_files DROP CONSTRAINT IF EXISTS chk_project_files_category;
ALTER TABLE public.project_files ADD CONSTRAINT chk_project_files_category
    CHECK (category IN (
        'documentation', 'source_code', 'screenshots', 'results', 'research', 
        'presentation', 'diagrams', 'previous_report', 'other',
        'dataset', 'code_sample', 'survey_results', 'notes', 'literature', 'system_output'
    ));

-- 3. Create project_members table
CREATE TABLE IF NOT EXISTS public.project_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    roll_number TEXT DEFAULT NULL,
    email TEXT DEFAULT NULL,
    role TEXT DEFAULT 'Member',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_project_members_project_id ON public.project_members(project_id);
CREATE INDEX IF NOT EXISTS idx_project_members_user_id ON public.project_members(user_id);

-- Enable RLS on project_members
ALTER TABLE public.project_members ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Users can manage members of their own projects" ON public.project_members;
DROP POLICY IF EXISTS "Users can view members of their own projects" ON public.project_members;
DROP POLICY IF EXISTS "Service role can manage all project members" ON public.project_members;

-- RLS policies for project_members
CREATE POLICY "Users can manage members of their own projects"
    ON public.project_members
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.projects p
            WHERE p.id = project_members.project_id
            AND (p.user_id = auth.uid() OR p.owner_id = auth.uid())
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.projects p
            WHERE p.id = project_members.project_id
            AND (p.user_id = auth.uid() OR p.owner_id = auth.uid())
        )
    );

CREATE POLICY "Service role can manage all project members"
    ON public.project_members
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Comments
COMMENT ON TABLE public.project_members IS 'Team members and collaborators assigned to an academic project';
COMMENT ON COLUMN public.projects.problem_statement IS 'Problem statement defining what the project solves';
COMMENT ON COLUMN public.projects.objectives IS 'Bullet points or description of academic project objectives';
COMMENT ON COLUMN public.projects.scope IS 'Scope and boundaries of the project';
COMMENT ON COLUMN public.projects.methodology IS 'Methodology, algorithms, or engineering process followed';
COMMENT ON COLUMN public.projects.expected_outcome IS 'Expected outcomes and results';
COMMENT ON COLUMN public.projects.actual_outcome IS 'Actual achieved outcomes';
COMMENT ON COLUMN public.project_files.sha256_hash IS 'Cryptographic SHA-256 checksum for tamper detection and deduplication';
