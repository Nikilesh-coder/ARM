-- ==============================================================================
-- ARM Stage 11 Migration: Report Validation + Quality Engine
-- Creates report_validations table with structured JSONB storage, audit metadata,
-- input hashes for stale validation detection, foreign keys, performance indexes,
-- and strict Row Level Security.
-- Preserves all Stages 1-10 schemas without breaking changes.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.report_validations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_version_id UUID NOT NULL REFERENCES public.report_versions(id) ON DELETE CASCADE,
    report_id UUID NOT NULL REFERENCES public.reports(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    validator_version TEXT NOT NULL DEFAULT '1.0.0',
    status TEXT NOT NULL DEFAULT 'ready',
    gate_status TEXT NOT NULL DEFAULT 'ready',
    validation_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    checks JSONB NOT NULL DEFAULT '[]'::jsonb,
    issues JSONB NOT NULL DEFAULT '[]'::jsonb,
    input_hashes JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_stale BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Status check constraint
ALTER TABLE public.report_validations DROP CONSTRAINT IF EXISTS chk_report_validations_status;
ALTER TABLE public.report_validations ADD CONSTRAINT chk_report_validations_status
    CHECK (status IN ('ready', 'ready_with_warnings', 'review_required', 'blocked', 'failed', 'stale'));

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_report_validations_project_id ON public.report_validations(project_id);
CREATE INDEX IF NOT EXISTS idx_report_validations_report_id ON public.report_validations(report_id);
CREATE INDEX IF NOT EXISTS idx_report_validations_report_version_id ON public.report_validations(report_version_id);
CREATE INDEX IF NOT EXISTS idx_report_validations_user_id ON public.report_validations(user_id);
CREATE INDEX IF NOT EXISTS idx_report_validations_status ON public.report_validations(status);
CREATE INDEX IF NOT EXISTS idx_report_validations_created_at ON public.report_validations(created_at DESC);

-- Enable RLS
ALTER TABLE public.report_validations ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Users can manage report validations for their own projects" ON public.report_validations;
DROP POLICY IF EXISTS "Service role can manage all report validations" ON public.report_validations;

-- RLS policies
CREATE POLICY "Users can manage report validations for their own projects"
    ON public.report_validations
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.projects p
            WHERE p.id = report_validations.project_id
            AND (p.user_id = auth.uid() OR p.owner_id = auth.uid())
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.projects p
            WHERE p.id = report_validations.project_id
            AND (p.user_id = auth.uid() OR p.owner_id = auth.uid())
        )
    );

CREATE POLICY "Service role can manage all report validations"
    ON public.report_validations
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Comments
COMMENT ON TABLE public.report_validations IS 'Stage 11: Authoritative structured report validation and quality engine records';
COMMENT ON COLUMN public.report_validations.validator_version IS 'Version of the quality validation engine';
COMMENT ON COLUMN public.report_validations.status IS 'Quality gate verdict: ready, ready_with_warnings, review_required, blocked, failed';
COMMENT ON COLUMN public.report_validations.validation_summary IS 'Factual summary of total checks, pass/fail, and severity tallies';
COMMENT ON COLUMN public.report_validations.checks IS 'Detailed list of individual layer validation checks';
COMMENT ON COLUMN public.report_validations.issues IS 'List of detected issues with severity, affected sections, and recommendations';
COMMENT ON COLUMN public.report_validations.input_hashes IS 'Cryptographic hashes of inputs (content, docx, pdf, template) for stale detection';
