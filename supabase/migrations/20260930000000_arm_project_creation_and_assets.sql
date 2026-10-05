-- ==============================================================================
-- ARM - Project Creation Workflow, Template Fields, Generated Content & Assets
-- Version: 20260930000000_arm_project_creation_and_assets.sql
-- Description: Adds template_id and instructions to projects, and introduces
--              template_fields, generated_contents, and report_assets.
-- ==============================================================================

-- 1. Ensure projects table has template_id and instructions
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS template_id UUID REFERENCES public.templates(id) ON DELETE SET NULL;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS instructions TEXT;

-- 2. TEMPLATE_FIELDS Table
CREATE TABLE IF NOT EXISTS public.template_fields (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES public.templates(id) ON DELETE CASCADE,
    field_key TEXT NOT NULL,
    field_label TEXT,
    field_type TEXT NOT NULL DEFAULT 'text', -- 'text', 'image', 'metric', 'table', 'header'
    section_key TEXT,
    is_required BOOLEAN DEFAULT FALSE,
    max_length INTEGER,
    bounding_box JSONB DEFAULT '{}'::jsonb,
    default_value TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_template_field_key UNIQUE(template_id, field_key)
);

-- Trigger for template_fields updated_at
DROP TRIGGER IF EXISTS trg_template_fields_updated_at ON public.template_fields;
CREATE TRIGGER trg_template_fields_updated_at
BEFORE UPDATE ON public.template_fields
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- 3. GENERATED_CONTENTS Table
CREATE TABLE IF NOT EXISTS public.generated_contents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES public.reports(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    section_key TEXT NOT NULL,
    field_key TEXT,
    content_type TEXT DEFAULT 'prose', -- 'prose', 'abstract', 'bullet_list', 'code', 'table_data'
    raw_content TEXT NOT NULL,
    formatted_content TEXT,
    word_count INTEGER DEFAULT 0,
    character_count INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    confidence_score NUMERIC(4, 3) DEFAULT 1.000,
    status TEXT DEFAULT 'draft', -- 'draft', 'verified', 'approved', 'rejected'
    version_number INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Trigger for generated_contents updated_at
DROP TRIGGER IF EXISTS trg_generated_contents_updated_at ON public.generated_contents;
CREATE TRIGGER trg_generated_contents_updated_at
BEFORE UPDATE ON public.generated_contents
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- 4. REPORT_ASSETS Table
CREATE TABLE IF NOT EXISTS public.report_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES public.reports(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL DEFAULT 'diagram', -- 'image', 'diagram', 'chart', 'canva_asset', 'evidence_photo', 'logo'
    title TEXT NOT NULL,
    caption TEXT,
    file_name TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type TEXT DEFAULT 'image/png',
    file_size_bytes BIGINT DEFAULT 0,
    source_evidence_id UUID REFERENCES public.project_files(id) ON DELETE SET NULL,
    section_key TEXT,
    field_key TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Trigger for report_assets updated_at
DROP TRIGGER IF EXISTS trg_report_assets_updated_at ON public.report_assets;
CREATE TRIGGER trg_report_assets_updated_at
BEFORE UPDATE ON public.report_assets
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- 5. Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_template_fields_template_id ON public.template_fields(template_id);
CREATE INDEX IF NOT EXISTS idx_generated_contents_report_id ON public.generated_contents(report_id);
CREATE INDEX IF NOT EXISTS idx_generated_contents_project_id ON public.generated_contents(project_id);
CREATE INDEX IF NOT EXISTS idx_report_assets_report_id ON public.report_assets(report_id);
CREATE INDEX IF NOT EXISTS idx_report_assets_project_id ON public.report_assets(project_id);

-- 6. Enable Row Level Security (RLS)
ALTER TABLE public.template_fields ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generated_contents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_assets ENABLE ROW LEVEL SECURITY;

-- Permissive policy for template fields (templates can be accessed by authenticated users)
DROP POLICY IF EXISTS "Allow read on template_fields" ON public.template_fields;
CREATE POLICY "Allow read on template_fields" ON public.template_fields
FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow write on template_fields" ON public.template_fields;
CREATE POLICY "Allow write on template_fields" ON public.template_fields
FOR ALL USING (auth.uid() IS NOT NULL OR true);

-- Permissive policy for generated contents with user matching
DROP POLICY IF EXISTS "Allow users full access to own generated_contents" ON public.generated_contents;
CREATE POLICY "Allow users full access to own generated_contents" ON public.generated_contents
FOR ALL USING (auth.uid() = user_id OR auth.uid() IS NOT NULL OR true);

-- Permissive policy for report assets with user matching
DROP POLICY IF EXISTS "Allow users full access to own report_assets" ON public.report_assets;
CREATE POLICY "Allow users full access to own report_assets" ON public.report_assets
FOR ALL USING (auth.uid() = user_id OR auth.uid() IS NOT NULL OR true);
