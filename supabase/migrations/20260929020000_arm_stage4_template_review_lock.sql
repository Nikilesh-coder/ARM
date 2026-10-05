-- ==============================================================================
-- ARM Stage 4 Migration: Template Review + Lock
-- Adds reviewed_schema, locked_schema, review and lock audit metadata
-- Preserves all Stage 1, Stage 2, and Stage 3 structures
-- ==============================================================================

-- 1. Extend templates table with lock audit columns
ALTER TABLE public.templates 
    ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS locked_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS locked_schema_version TEXT DEFAULT NULL;

-- 2. Extend template_analysis table with review & lock snapshots
ALTER TABLE public.template_analysis 
    ADD COLUMN IF NOT EXISTS reviewed_schema JSONB DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS locked_schema JSONB DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS reviewed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS locked_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- 3. Add performance indexes for lock and review status queries
CREATE INDEX IF NOT EXISTS idx_templates_is_locked ON public.templates(is_locked);
CREATE INDEX IF NOT EXISTS idx_templates_status ON public.templates(status);
CREATE INDEX IF NOT EXISTS idx_template_analysis_review_status ON public.template_analysis(review_status);

-- 4. Update templates status constraint to include reviewing and locked
ALTER TABLE public.templates DROP CONSTRAINT IF EXISTS chk_templates_status;
ALTER TABLE public.templates ADD CONSTRAINT chk_templates_status
    CHECK (status IN ('uploaded', 'analyzing', 'analyzed', 'reviewing', 'confirmed', 'locked', 'failed', 'analysis_failed'));

COMMENT ON COLUMN public.templates.locked_at IS 'Timestamp when the template structure was explicitly locked by the student';
COMMENT ON COLUMN public.templates.locked_by IS 'User ID who confirmed and locked the template';
COMMENT ON COLUMN public.templates.locked_schema_version IS 'Schema version of the locked authoritative template';

COMMENT ON COLUMN public.template_analysis.reviewed_schema IS 'Student-reviewed corrections and rule definitions';
COMMENT ON COLUMN public.template_analysis.locked_schema IS 'Immutable authoritative template schema snapshot at lock time';
COMMENT ON COLUMN public.template_analysis.review_status IS 'Lifecycle state: pending_review, in_review, reviewed, locked';
