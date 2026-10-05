-- ==============================================================================
-- ARM Migration: Automatic Image System & Report Asset Schema Enhancement
-- ==============================================================================

-- 1. Make report_id nullable in report_assets to allow project-level asset creation
ALTER TABLE public.report_assets ALTER COLUMN report_id DROP NOT NULL;

-- 2. Add explicit columns for the automatic image asset pipeline
ALTER TABLE public.report_assets ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'generated';
ALTER TABLE public.report_assets ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE public.report_assets ADD COLUMN IF NOT EXISTS template_field TEXT;
ALTER TABLE public.report_assets ADD COLUMN IF NOT EXISTS attribution TEXT DEFAULT 'Synthesized via ARM Technical Visual Engine; Open Academic Commons';
ALTER TABLE public.report_assets ADD COLUMN IF NOT EXISTS license_info TEXT DEFAULT 'CC-BY-4.0 / Academic Open';

-- 3. Create sync triggers between template_field <-> field_key and description <-> caption
CREATE OR REPLACE FUNCTION public.sync_report_asset_fields()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.template_field IS NOT NULL AND NEW.field_key IS NULL THEN
        NEW.field_key := NEW.template_field;
    ELSIF NEW.field_key IS NOT NULL AND NEW.template_field IS NULL THEN
        NEW.template_field := NEW.field_key;
    END IF;

    IF NEW.description IS NOT NULL AND NEW.caption IS NULL THEN
        NEW.caption := NEW.description;
    ELSIF NEW.caption IS NOT NULL AND NEW.description IS NULL THEN
        NEW.description := NEW.caption;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_report_asset_fields ON public.report_assets;
CREATE TRIGGER trg_sync_report_asset_fields
BEFORE INSERT OR UPDATE ON public.report_assets
FOR EACH ROW EXECUTE FUNCTION public.sync_report_asset_fields();

-- 4. Index on template_field for fast replacement queries
CREATE INDEX IF NOT EXISTS idx_report_assets_template_field ON public.report_assets(template_field);
