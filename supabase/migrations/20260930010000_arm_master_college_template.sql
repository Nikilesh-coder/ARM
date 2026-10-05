-- ==============================================================================
-- ARM - Master College Template & Fixed Field System
-- Version: 20260930010000_arm_master_college_template.sql
-- Description: Establishes Master Template configuration, enriches TemplateField
--              with typed limits, dimensions, ordering, and seeds 20 canonical fields.
-- ==============================================================================

-- 1. Extend templates table with master template attributes
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS is_master BOOLEAN DEFAULT FALSE;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS institution TEXT;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS department TEXT;
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS master_version TEXT DEFAULT '1.0.0';
ALTER TABLE public.templates ADD COLUMN IF NOT EXISTS description TEXT;

-- 2. Extend template_fields table with requested model attributes
ALTER TABLE public.template_fields ADD COLUMN IF NOT EXISTS field_name TEXT;
ALTER TABLE public.template_fields ADD COLUMN IF NOT EXISTS page_or_section TEXT;
ALTER TABLE public.template_fields ADD COLUMN IF NOT EXISTS placeholder_identifier TEXT;
ALTER TABLE public.template_fields ADD COLUMN IF NOT EXISTS content_limits JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.template_fields ADD COLUMN IF NOT EXISTS image_dimensions JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.template_fields ADD COLUMN IF NOT EXISTS ordering INTEGER DEFAULT 0;

-- Sync field_key and field_name, section_key and page_or_section
CREATE OR REPLACE FUNCTION public.sync_template_field_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.field_name IS NULL AND NEW.field_key IS NOT NULL THEN
        NEW.field_name := NEW.field_key;
    END IF;
    IF NEW.field_key IS NULL AND NEW.field_name IS NOT NULL THEN
        NEW.field_key := NEW.field_name;
    END IF;
    IF NEW.page_or_section IS NULL AND NEW.section_key IS NOT NULL THEN
        NEW.page_or_section := NEW.section_key;
    END IF;
    IF NEW.section_key IS NULL AND NEW.page_or_section IS NOT NULL THEN
        NEW.section_key := NEW.page_or_section;
    END IF;
    IF NEW.placeholder_identifier IS NULL AND NEW.field_name IS NOT NULL THEN
        NEW.placeholder_identifier := '{{' || UPPER(NEW.field_name) || '}}';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_template_field_columns ON public.template_fields;
CREATE TRIGGER trg_sync_template_field_columns
BEFORE INSERT OR UPDATE ON public.template_fields
FOR EACH ROW EXECUTE FUNCTION public.sync_template_field_columns();

-- 3. Seed Canonical Master College Template
INSERT INTO public.templates (
    id,
    name,
    original_file_path,
    file_type,
    file_size_bytes,
    is_master,
    is_institution_preset,
    is_locked,
    status,
    master_version,
    description,
    institution,
    department
)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Standard College Academic Report Master Template',
    '.storage/templates/master_college_template.docx',
    'docx',
    42800,
    TRUE,
    TRUE,
    TRUE,
    'locked',
    '1.0.0',
    'Authoritative Fixed College Report Template. Typography, margins, headers, and footers are locked. Content and images are automated via 20 configurable fields.',
    'College of Engineering & Technology',
    'Department of Computer Science & Engineering'
)
ON CONFLICT (id) DO UPDATE SET
    is_master = TRUE,
    is_institution_preset = TRUE,
    is_locked = TRUE,
    status = 'locked',
    master_version = '1.0.0',
    description = EXCLUDED.description;

-- 4. Seed the 20 Reusable College Fields
DELETE FROM public.template_fields WHERE template_id = '00000000-0000-0000-0000-000000000001';

INSERT INTO public.template_fields (
    template_id, field_key, field_name, field_label, field_type,
    section_key, page_or_section, is_required, placeholder_identifier,
    content_limits, image_dimensions, ordering
) VALUES
-- 1. Project Title
(
    '00000000-0000-0000-0000-000000000001',
    'project_title', 'project_title', 'Project Title', 'text',
    'Cover Page', 'Cover Page', TRUE, '{{PROJECT_TITLE}}',
    '{"min_length": 5, "max_length": 150}'::jsonb, '{}'::jsonb, 1
),
-- 2. Student Name
(
    '00000000-0000-0000-0000-000000000001',
    'student_name', 'student_name', 'Student Scholar Name', 'text',
    'Cover Page', 'Cover Page', TRUE, '{{STUDENT_NAME}}',
    '{"min_length": 2, "max_length": 80}'::jsonb, '{}'::jsonb, 2
),
-- 3. Roll Number
(
    '00000000-0000-0000-0000-000000000001',
    'roll_number', 'roll_number', 'University Roll / Registration Number', 'text',
    'Cover Page', 'Cover Page', TRUE, '{{ROLL_NUMBER}}',
    '{"min_length": 4, "max_length": 30}'::jsonb, '{}'::jsonb, 3
),
-- 4. Department
(
    '00000000-0000-0000-0000-000000000001',
    'department', 'department', 'Academic Department', 'text',
    'Cover Page', 'Cover Page', TRUE, '{{DEPARTMENT}}',
    '{"min_length": 4, "max_length": 100}'::jsonb, '{}'::jsonb, 4
),
-- 5. Guide Name
(
    '00000000-0000-0000-0000-000000000001',
    'guide_name', 'guide_name', 'Faculty Supervisor / Guide Name', 'text',
    'Cover Page / Certificate', 'Cover Page / Certificate', TRUE, '{{GUIDE_NAME}}',
    '{"min_length": 3, "max_length": 100}'::jsonb, '{}'::jsonb, 5
),
-- 6. Introduction
(
    '00000000-0000-0000-0000-000000000001',
    'introduction', 'introduction', 'Chapter 1: Introduction', 'long_text',
    'Introduction', 'Chapter 1: Introduction', TRUE, '{{INTRODUCTION}}',
    '{"min_words": 300, "max_words": 800}'::jsonb, '{}'::jsonb, 6
),
-- 7. Objectives
(
    '00000000-0000-0000-0000-000000000001',
    'objectives', 'objectives', 'Project Objectives', 'list',
    'Objectives', 'Objectives', TRUE, '{{OBJECTIVES}}',
    '{"min_items": 3, "max_items": 6}'::jsonb, '{}'::jsonb, 7
),
-- 8. Problem Statement
(
    '00000000-0000-0000-0000-000000000001',
    'problem_statement', 'problem_statement', 'Problem Statement & Motivation', 'long_text',
    'Problem Statement', 'Problem Statement', TRUE, '{{PROBLEM_STATEMENT}}',
    '{"min_words": 200, "max_words": 500}'::jsonb, '{}'::jsonb, 8
),
-- 9. Methodology
(
    '00000000-0000-0000-0000-000000000001',
    'methodology', 'methodology', 'Chapter 2: System Methodology & Architecture', 'long_text',
    'Methodology', 'Chapter 2: System Methodology', TRUE, '{{METHODOLOGY}}',
    '{"min_words": 400, "max_words": 1000}'::jsonb, '{}'::jsonb, 9
),
-- 10. Technologies
(
    '00000000-0000-0000-0000-000000000001',
    'technologies', 'technologies', 'Tech Stack & Frameworks', 'list',
    'Technologies', 'Technologies', TRUE, '{{TECHNOLOGIES}}',
    '{"min_items": 3, "max_items": 10}'::jsonb, '{}'::jsonb, 10
),
-- 11. Implementation
(
    '00000000-0000-0000-0000-000000000001',
    'implementation', 'implementation', 'Chapter 3: Implementation & Execution', 'long_text',
    'Implementation', 'Chapter 3: Implementation', TRUE, '{{IMPLEMENTATION}}',
    '{"min_words": 500, "max_words": 1200}'::jsonb, '{}'::jsonb, 11
),
-- 12. Results
(
    '00000000-0000-0000-0000-000000000001',
    'results', 'results', 'Chapter 4: Experimental Results & Analysis', 'long_text',
    'Results', 'Chapter 4: Results & Analysis', TRUE, '{{RESULTS}}',
    '{"min_words": 300, "max_words": 800}'::jsonb, '{}'::jsonb, 12
),
-- 13. Advantages
(
    '00000000-0000-0000-0000-000000000001',
    'advantages', 'advantages', 'System Advantages', 'list',
    'Advantages', 'Advantages', FALSE, '{{ADVANTAGES}}',
    '{"min_items": 3, "max_items": 6}'::jsonb, '{}'::jsonb, 13
),
-- 14. Limitations
(
    '00000000-0000-0000-0000-000000000001',
    'limitations', 'limitations', 'System Constraints & Limitations', 'list',
    'Limitations', 'Limitations', FALSE, '{{LIMITATIONS}}',
    '{"min_items": 2, "max_items": 5}'::jsonb, '{}'::jsonb, 14
),
-- 15. Future Scope
(
    '00000000-0000-0000-0000-000000000001',
    'future_scope', 'future_scope', 'Future Scope & Enhancements', 'long_text',
    'Future Scope', 'Future Scope', FALSE, '{{FUTURE_SCOPE}}',
    '{"min_words": 150, "max_words": 400}'::jsonb, '{}'::jsonb, 15
),
-- 16. Conclusion
(
    '00000000-0000-0000-0000-000000000001',
    'conclusion', 'conclusion', 'Chapter 5: Conclusion', 'long_text',
    'Conclusion', 'Chapter 5: Conclusion', TRUE, '{{CONCLUSION}}',
    '{"min_words": 200, "max_words": 500}'::jsonb, '{}'::jsonb, 16
),
-- 17. References
(
    '00000000-0000-0000-0000-000000000001',
    'references', 'references', 'Academic References & Bibliography', 'list',
    'References', 'References', TRUE, '{{REFERENCES}}',
    '{"min_items": 5, "max_items": 20}'::jsonb, '{}'::jsonb, 17
),
-- 18. Image 1: Architecture / System Diagram
(
    '00000000-0000-0000-0000-000000000001',
    'image_1', 'image_1', 'Figure 1: System Architecture Diagram', 'image',
    'Methodology', 'Chapter 2: System Methodology', TRUE, '{{IMAGE_1}}',
    '{}'::jsonb, '{"width": 800, "height": 500, "aspect_ratio": "16:9", "dpi": 300}'::jsonb, 18
),
-- 19. Image 2: Implementation / Evidence Photo
(
    '00000000-0000-0000-0000-000000000001',
    'image_2', 'image_2', 'Figure 2: Implementation Setup / Evidence Photo', 'image',
    'Implementation', 'Chapter 3: Implementation', FALSE, '{{IMAGE_2}}',
    '{}'::jsonb, '{"width": 800, "height": 500, "aspect_ratio": "16:9", "dpi": 300}'::jsonb, 19
),
-- 20. Image 3: Results Graph / Chart
(
    '00000000-0000-0000-0000-000000000001',
    'image_3', 'image_3', 'Figure 3: Empirical Performance Graph / Chart', 'image',
    'Results', 'Chapter 4: Results & Analysis', FALSE, '{{IMAGE_3}}',
    '{}'::jsonb, '{"width": 800, "height": 500, "aspect_ratio": "16:9", "dpi": 300}'::jsonb, 20
);
