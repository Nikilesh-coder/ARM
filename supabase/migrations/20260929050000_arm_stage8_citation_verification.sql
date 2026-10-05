-- ==============================================================================
-- ARM Stage 8 Migration: Citation + Evidence Verification
-- Creates report_verifications table with structured JSONB storage, audit metadata,
-- foreign keys, performance indexes, and strict Row Level Security.
-- Preserves all Stages 1-7 schemas without breaking changes.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.report_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_version_id UUID NOT NULL REFERENCES public.report_versions(id) ON DELETE CASCADE,
    report_id UUID NOT NULL REFERENCES public.reports(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    verifier_version TEXT NOT NULL DEFAULT '1.0.0',
    verification_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    quality_gates JSONB NOT NULL DEFAULT '{}'::jsonb,
    claims JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Status check constraint
ALTER TABLE public.report_verifications DROP CONSTRAINT IF EXISTS chk_report_verifications_status;
ALTER TABLE public.report_verifications ADD CONSTRAINT chk_report_verifications_status
    CHECK (status IN ('queued', 'verifying', 'completed', 'failed', 'stale'));

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_report_verifications_project_id ON public.report_verifications(project_id);
CREATE INDEX IF NOT EXISTS idx_report_verifications_report_id ON public.report_verifications(report_id);
CREATE INDEX IF NOT EXISTS idx_report_verifications_report_version_id ON public.report_verifications(report_version_id);
CREATE INDEX IF NOT EXISTS idx_report_verifications_user_id ON public.report_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_report_verifications_status ON public.report_verifications(status);
CREATE INDEX IF NOT EXISTS idx_report_verifications_created_at ON public.report_verifications(created_at DESC);

-- Enable RLS
ALTER TABLE public.report_verifications ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Users can manage report verifications for their own projects" ON public.report_verifications;
DROP POLICY IF EXISTS "Service role can manage all report verifications" ON public.report_verifications;

-- RLS policies
CREATE POLICY "Users can manage report verifications for their own projects"
    ON public.report_verifications
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.projects p
            WHERE p.id = report_verifications.project_id
            AND (p.user_id = auth.uid() OR p.owner_id = auth.uid())
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.projects p
            WHERE p.id = report_verifications.project_id
            AND (p.user_id = auth.uid() OR p.owner_id = auth.uid())
        )
    );

CREATE POLICY "Service role can manage all report verifications"
    ON public.report_verifications
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Comments
COMMENT ON TABLE public.report_verifications IS 'Stage 8: Authoritative structured citation and evidence verification records';
COMMENT ON COLUMN public.report_verifications.verifier_version IS 'Version of the verification engine algorithms';
COMMENT ON COLUMN public.report_verifications.verification_summary IS 'Aggregate metric breakdown of claim statuses and grounding rates';
COMMENT ON COLUMN public.report_verifications.quality_gates IS 'Blocking and non-blocking document generation readiness assessments';
COMMENT ON COLUMN public.report_verifications.claims IS 'Array of validated claim records with evidence and provenance mappings';
