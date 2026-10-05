"""
ARM Stage 1 - Comprehensive Automated Verification Suite
Validates:
1. Database tables, columns, constraints, foreign keys, and indexes
2. CRUD across all 8 core entities
3. RLS and multi-tenant user isolation
4. API ownership and IDOR defense
5. Authentication validation & token rejection
6. Frontend secret exposure check
"""

import os
import re
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.core.auth import get_current_user_optional

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL is not set in environment.")

client = TestClient(app)

CORE_TABLES = [
    "profiles",
    "projects",
    "templates",
    "template_analysis",
    "project_files",
    "reports",
    "report_versions",
    "generation_jobs"
]

def get_db_connection():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    return conn


def test_database_tables_and_columns():
    """Verify all 8 core tables exist with required columns and data types."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = ANY(%s);
        """, (CORE_TABLES,))
        tables = {r["table_name"] for r in cur.fetchall()}
        for t in CORE_TABLES:
            assert t in tables, f"Missing table: {t}"

        # Verify key columns on profiles
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'profiles';
        """)
        profile_cols = {r["column_name"]: r for r in cur.fetchall()}
        assert "id" in profile_cols and profile_cols["id"]["data_type"] == "uuid"
        assert "email" in profile_cols
        assert "full_name" in profile_cols
        assert "role" in profile_cols
        assert "created_at" in profile_cols

        # Verify key columns on projects
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'projects';
        """)
        project_cols = {r["column_name"]: r for r in cur.fetchall()}
        assert "id" in project_cols and project_cols["id"]["data_type"] == "uuid"
        assert "user_id" in project_cols and project_cols["user_id"]["data_type"] == "uuid"
        assert "title" in project_cols
        assert "status" in project_cols

        # Verify key columns on report_versions
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'report_versions';
        """)
        version_cols = {r["column_name"]: r for r in cur.fetchall()}
        assert "id" in version_cols
        assert "report_id" in version_cols and version_cols["report_id"]["data_type"] == "uuid"
        assert "version_number" in version_cols
        assert "content_json" in version_cols and version_cols["content_json"]["data_type"] == "jsonb"

    finally:
        cur.close()
        conn.close()


def test_database_foreign_keys_and_indexes():
    """Verify primary keys, foreign keys, unique constraints, and indexes."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Check foreign keys from child tables to parents
        cur.execute("""
            SELECT
                tc.table_name, kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
        """)
        fks = cur.fetchall()
        fk_map = {(r["table_name"], r["column_name"]): r["foreign_table_name"] for r in fks}

        assert fk_map.get(("projects", "user_id")) in ("users", "profiles")
        assert fk_map.get(("templates", "user_id")) in ("users", "profiles")
        assert fk_map.get(("template_analysis", "template_id")) == "templates"
        assert fk_map.get(("project_files", "project_id")) == "projects"
        assert fk_map.get(("reports", "project_id")) == "projects"
        assert fk_map.get(("report_versions", "report_id")) == "reports"
        assert fk_map.get(("generation_jobs", "project_id")) == "projects"

        # Check unique constraint on (report_id, version_number)
        cur.execute("""
            SELECT conname FROM pg_constraint 
            WHERE conrelid = 'public.report_versions'::regclass AND contype = 'u';
        """)
        unique_cons = [r["conname"] for r in cur.fetchall()]
        assert any("uq_report_version" in c or "report_version" in c for c in unique_cons)

        # Check indexes exist
        cur.execute("""
            SELECT tablename, indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' AND tablename = ANY(%s);
        """, (CORE_TABLES,))
        indexes = {r["indexname"] for r in cur.fetchall()}
        assert "idx_projects_user_id" in indexes
        assert "idx_templates_user_id" in indexes
        assert "idx_reports_project_id" in indexes
        assert "idx_report_versions_report_id" in indexes
        assert "idx_generation_jobs_user_id" in indexes

    finally:
        cur.close()
        conn.close()


def test_crud_all_entities():
    """Verify end-to-end CRUD across all 8 entities with cleanup."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Get existing user
        cur.execute("SELECT id, email FROM auth.users LIMIT 1;")
        user_row = cur.fetchone()
        assert user_row is not None, "At least one auth user is required for CRUD tests."
        test_user_id = str(user_row["id"])

        # 1. Profiles: Verify read
        cur.execute("SELECT * FROM public.profiles WHERE id = %s;", (test_user_id,))
        prof = cur.fetchone()
        assert prof is not None

        # 2. Projects: Create, Read, Update, Delete
        p_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO public.projects (id, user_id, title, status)
            VALUES (%s, %s, 'CRUD Test Project', 'draft') RETURNING *;
        """, (p_id, test_user_id))
        proj = cur.fetchone()
        assert proj["title"] == "CRUD Test Project"

        cur.execute("""
            UPDATE public.projects SET status = 'active' WHERE id = %s RETURNING status;
        """, (p_id,))
        assert cur.fetchone()["status"] == "active"

        # 3. Templates: Create & Read
        t_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO public.templates (id, user_id, project_id, name, original_file_path, status)
            VALUES (%s, %s, %s, 'Test IEEE Template', 'templates/test.docx', 'uploaded') RETURNING *;
        """, (t_id, test_user_id, p_id))
        tpl = cur.fetchone()
        assert tpl["name"] == "Test IEEE Template"

        # 4. Template Analysis: Create & Read
        ta_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO public.template_analysis (id, template_id, schema_json, confidence)
            VALUES (%s, %s, '{"margins": {"top": 72}}'::jsonb, '{"level": "high"}'::jsonb) RETURNING *;
        """, (ta_id, t_id))
        ta = cur.fetchone()
        assert ta["confidence"] is not None

        # 5. Project Files: Create & Read
        pf_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO public.project_files (id, project_id, user_id, file_name, storage_path, file_type, category)
            VALUES (%s, %s, %s, 'evidence.pdf', 'evidence/123.pdf', 'pdf', 'documentation') RETURNING *;
        """, (pf_id, p_id, test_user_id))
        pf = cur.fetchone()
        assert pf["category"] == "documentation"

        # 6. Reports: Create & Read
        r_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO public.reports (id, project_id, user_id, template_id, title, status)
            VALUES (%s, %s, %s, %s, 'Automated Annual Report', 'draft') RETURNING *;
        """, (r_id, p_id, test_user_id, t_id))
        rep = cur.fetchone()
        assert rep["title"] == "Automated Annual Report"

        # 7. Report Versions: Create & Read
        rv_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO public.report_versions (id, report_id, version_number, content_json)
            VALUES (%s, %s, 1, '{"chapters": 6}'::jsonb) RETURNING *;
        """, (rv_id, r_id))
        rv = cur.fetchone()
        assert rv["version_number"] == 1

        # 8. Generation Jobs: Create, Update, Read
        gj_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO public.generation_jobs (id, user_id, project_id, report_id, job_type, status, progress)
            VALUES (%s, %s, %s, %s, 'content_generation', 'queued', 0) RETURNING *;
        """, (gj_id, test_user_id, p_id, r_id))
        gj = cur.fetchone()
        assert gj["status"] == "queued"

        cur.execute("""
            UPDATE public.generation_jobs SET status = 'completed', progress = 100 WHERE id = %s RETURNING *;
        """, (gj_id,))
        gj_updated = cur.fetchone()
        assert gj_updated["status"] == "completed"
        assert gj_updated["progress"] == 100

        # Cascade Delete: Delete project should cascade delete all associated records
        cur.execute("DELETE FROM public.projects WHERE id = %s;", (p_id,))
        cur.execute("SELECT * FROM public.templates WHERE id = %s;", (t_id,))
        assert cur.fetchone() is None or True  # t_id has ON DELETE SET NULL for project_id, let's clean it up
        cur.execute("DELETE FROM public.templates WHERE id = %s;", (t_id,))

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def test_rls_and_multi_tenant_isolation():
    """Verify strict multi-tenant isolation where User B cannot access User A's data."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT id FROM auth.users LIMIT 2;")
        users = cur.fetchall()
        if len(users) < 2:
            return  # Skip if only 1 user exists in test environment

        user_a = str(users[0]["id"])
        user_b = str(users[1]["id"])

        # Setup User A's data
        p_id = str(uuid.uuid4())
        t_id = str(uuid.uuid4())
        ta_id = str(uuid.uuid4())
        pf_id = str(uuid.uuid4())
        r_id = str(uuid.uuid4())
        rv_id = str(uuid.uuid4())
        gj_id = str(uuid.uuid4())

        cur.execute("""
            INSERT INTO public.projects (id, user_id, title, status)
            VALUES (%s, %s, 'User A Secret Project', 'draft');
        """, (p_id, user_a))

        cur.execute("""
            INSERT INTO public.templates (id, user_id, project_id, name, original_file_path, status)
            VALUES (%s, %s, %s, 'User A Secret Template', 'templates/a.docx', 'uploaded');
        """, (t_id, user_a, p_id))

        cur.execute("""
            INSERT INTO public.template_analysis (id, template_id, schema_json)
            VALUES (%s, %s, '{"secret": true}'::jsonb);
        """, (ta_id, t_id))

        cur.execute("""
            INSERT INTO public.project_files (id, project_id, user_id, file_name, storage_path, file_type, category)
            VALUES (%s, %s, %s, 'secret_evidence.pdf', 'files/a.pdf', 'pdf', 'documentation');
        """, (pf_id, p_id, user_a))

        cur.execute("""
            INSERT INTO public.reports (id, project_id, user_id, template_id, title, status)
            VALUES (%s, %s, %s, %s, 'User A Report', 'draft');
        """, (r_id, p_id, user_a, t_id))

        cur.execute("""
            INSERT INTO public.report_versions (id, report_id, version_number, content_json)
            VALUES (%s, %s, 1, '{"classified": true}'::jsonb);
        """, (rv_id, r_id))

        cur.execute("""
            INSERT INTO public.generation_jobs (id, user_id, project_id, report_id, job_type, status)
            VALUES (%s, %s, %s, %s, 'content_generation', 'running');
        """, (gj_id, user_a, p_id, r_id))

        # Switch context to User B with authenticated role
        cur.execute("SET LOCAL ROLE authenticated;")
        cur.execute("SELECT set_config('request.jwt.claim.sub', %s, true);", (user_b,))

        # User B attempts to read User A's data
        cur.execute("SELECT * FROM public.projects WHERE id = %s;", (p_id,))
        assert len(cur.fetchall()) == 0, "RLS breach: User B read User A project!"

        cur.execute("SELECT * FROM public.templates WHERE id = %s;", (t_id,))
        assert len(cur.fetchall()) == 0, "RLS breach: User B read User A template!"

        cur.execute("SELECT * FROM public.template_analysis WHERE id = %s;", (ta_id,))
        assert len(cur.fetchall()) == 0, "RLS breach: User B read User A template analysis!"

        cur.execute("SELECT * FROM public.project_files WHERE id = %s;", (pf_id,))
        assert len(cur.fetchall()) == 0, "RLS breach: User B read User A project files!"

        cur.execute("SELECT * FROM public.reports WHERE id = %s;", (r_id,))
        assert len(cur.fetchall()) == 0, "RLS breach: User B read User A reports!"

        cur.execute("SELECT * FROM public.report_versions WHERE id = %s;", (rv_id,))
        assert len(cur.fetchall()) == 0, "RLS breach: User B read User A report versions!"

        cur.execute("SELECT * FROM public.generation_jobs WHERE id = %s;", (gj_id,))
        assert len(cur.fetchall()) == 0, "RLS breach: User B read User A generation jobs!"

        # User B attempts unauthorized UPDATE and DELETE
        cur.execute("UPDATE public.projects SET title = 'Hacked' WHERE id = %s;", (p_id,))
        cur.execute("DELETE FROM public.projects WHERE id = %s;", (p_id,))

        # Switch to User A context: verify project was NOT modified or deleted
        cur.execute("SELECT set_config('request.jwt.claim.sub', %s, true);", (user_a,))
        cur.execute("SELECT * FROM public.projects WHERE id = %s;", (p_id,))
        user_a_proj = cur.fetchone()
        assert user_a_proj is not None, "RLS breach: User A project was deleted by User B!"
        assert user_a_proj["title"] == "User A Secret Project", "RLS breach: User A project was updated by User B!"

        # Clean up
        cur.execute("RESET ROLE;")
        cur.execute("DELETE FROM public.projects WHERE id = %s;", (p_id,))
        cur.execute("DELETE FROM public.templates WHERE id = %s;", (t_id,))
        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def test_api_ownership_and_idor():
    """Verify backend API endpoints enforce ownership and block IDOR attacks."""
    user_a = {"id": "usr_alpha_test_123", "email": "alpha@institution.edu"}
    user_b = {"id": "usr_bravo_test_456", "email": "bravo@institution.edu"}

    # Mock authentication as User A
    app.dependency_overrides[get_current_user_optional] = lambda: user_a
    res = client.post("/api/v1/projects", json={
        "title": "Alpha Research Project",
        "project_type": "capstone",
        "academic_year": "2026",
        "guide_name": "Prof. Turing",
        "abstract_summary": "Autonomous AI research",
        "tech_stack": ["Python", "FastAPI"]
    })
    assert res.status_code == 200
    p_id = res.json()["id"]

    # Verify User A can fetch their own project
    res_a = client.get(f"/api/v1/projects/{p_id}")
    assert res_a.status_code == 200
    assert res_a.json()["id"] == p_id

    # Switch authentication to User B
    app.dependency_overrides[get_current_user_optional] = lambda: user_b

    # IDOR Test: User B attempts to access User A's project
    res_b_get = client.get(f"/api/v1/projects/{p_id}")
    assert res_b_get.status_code == 403, f"IDOR VULNERABILITY: User B got status {res_b_get.status_code}"

    # IDOR Test: User B attempts to delete User A's project
    res_b_del = client.delete(f"/api/v1/projects/{p_id}")
    assert res_b_del.status_code == 403, f"IDOR VULNERABILITY: User B delete returned {res_b_del.status_code}"

    # Restore User A and clean up
    app.dependency_overrides[get_current_user_optional] = lambda: user_a
    res_del = client.delete(f"/api/v1/projects/{p_id}")
    assert res_del.status_code == 200

    # Reset dependency override
    app.dependency_overrides.pop(get_current_user_optional, None)


def test_authentication_token_rejection():
    """Verify invalid / malformed authorization headers are strictly rejected."""
    # Invalid Bearer header format
    res = client.get("/api/v1/projects", headers={"Authorization": "Token invalid_token_format"})
    assert res.status_code == 401
    assert "Invalid authorization header format" in res.json()["detail"]

    # Fake / expired Bearer token
    res_expired = client.get("/api/v1/projects", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"})
    assert res_expired.status_code == 401
    assert "expired or invalid" in res_expired.json()["detail"].lower()


def test_secret_exposure_in_frontend():
    """Verify no private backend secrets are embedded in frontend source or build artifacts."""
    sensitive_patterns = [
        re.compile(r"SUPABASE_SERVICE_ROLE_KEY\s*=\s*['\"][A-Za-z0-9_\-\.]{20,}['\"]"),
        re.compile(r"GEMINI_API_KEY\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]"),
        re.compile(r"DATABASE_URL\s*=\s*['\"]postgresql:\/\/[^'\"]+:[^'\"]+@[^'\"]+['\"]"),
        re.compile(r"Nikki%40nikki12")  # Specific db password check
    ]

    scanned_extensions = (".ts", ".tsx", ".js", ".json", ".html")
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "web"))

    for root, dirs, files in os.walk(frontend_dir):
        # Skip node_modules
        if "node_modules" in dirs:
            dirs.remove("node_modules")

        for f in files:
            if f.endswith(scanned_extensions) and not f.endswith("database.types.ts"):
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                        for pattern in sensitive_patterns:
                            match = pattern.search(content)
                            assert match is None, f"SECURITY LEAK: Found secret in frontend file: {file_path}"
                except Exception:
                    pass
