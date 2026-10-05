import os
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL is not set")

def test_database_foundation():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        print("\n--- 1. VERIFY CORE TABLES EXIST ---")
        expected_tables = [
            "profiles",
            "projects",
            "templates",
            "template_analysis",
            "project_files",
            "reports",
            "report_versions",
            "generation_jobs"
        ]
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name = ANY(%s);
        """, (expected_tables,))
        found_tables = {row["table_name"] for row in cur.fetchall()}
        print(f"Found tables: {found_tables}")
        for t in expected_tables:
            assert t in found_tables, f"Missing table: {t}"
        print("[PASS] All 8 core tables exist!")

        print("\n--- 2. VERIFY ROW LEVEL SECURITY (RLS) STATUS ---")
        cur.execute("""
            SELECT relname, relrowsecurity 
            FROM pg_class 
            WHERE relname = ANY(%s) AND relnamespace = 'public'::regnamespace;
        """, (expected_tables,))
        rls_rows = cur.fetchall()
        for row in rls_rows:
            table = row["relname"]
            is_rls_enabled = row["relrowsecurity"]
            print(f"Table {table}: RLS Enabled = {is_rls_enabled}")
            assert is_rls_enabled, f"RLS is NOT enabled on {table}"
        print("[PASS] RLS is enabled on all 8 tables!")

        print("\n--- 3. VERIFY RLS POLICIES EXIST ---")
        cur.execute("""
            SELECT tablename, policyname, cmd, roles 
            FROM pg_policies 
            WHERE schemaname = 'public' AND tablename = ANY(%s);
        """, (expected_tables,))
        policies = cur.fetchall()
        assert len(policies) > 0, "No RLS policies found"
        policy_tables = {p["tablename"] for p in policies}
        for t in expected_tables:
            assert t in policy_tables, f"No policy defined for table {t}"
            t_policies = [p["policyname"] for p in policies if p["tablename"] == t]
            print(f"  {t} policies: {t_policies}")
        print("[PASS] RLS policies configured across all 8 tables!")

        print("\n--- 4. VERIFY CONSTRAINTS & FOREIGN KEYS ---")
        cur.execute("""
            SELECT tc.table_name, tc.constraint_name, tc.constraint_type
            FROM information_schema.table_constraints tc
            WHERE tc.table_schema = 'public' AND tc.table_name = ANY(%s);
        """, (expected_tables,))
        constraints = cur.fetchall()
        print(f"Found {len(constraints)} constraints across core tables.")

        # Check report_versions unique constraint
        cur.execute("""
            SELECT conname FROM pg_constraint 
            WHERE conrelid = 'public.report_versions'::regclass 
              AND contype = 'u';
        """)
        unique_cons = [r["conname"] for r in cur.fetchall()]
        print(f"report_versions unique constraints: {unique_cons}")
        assert any("report_version" in name or "uq" in name for name in unique_cons), "Missing unique constraint on report_versions"

        print("\n--- 5. VERIFY ISOLATION & RLS ENFORCEMENT ---")
        # Fetch two existing users or create test users in auth.users
        cur.execute("SELECT id FROM auth.users LIMIT 2;")
        users = cur.fetchall()
        if len(users) < 2:
            print("Need at least 2 auth users to test isolation; found:", len(users))
        else:
            user_a = str(users[0]["id"])
            user_b = str(users[1]["id"])
            print(f"Testing RLS isolation between User A ({user_a}) and User B ({user_b})")

            # Create test project for user_a
            test_proj_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO public.projects (id, user_id, title, status)
                VALUES (%s, %s, 'User A Secret Thesis', 'draft');
            """, (test_proj_id, user_a))

            # Create test template for user_a
            test_tpl_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO public.templates (id, user_id, project_id, name, original_file_path, status)
                VALUES (%s, %s, %s, 'IEEE Template A', 'templates/ieee.docx', 'uploaded');
            """, (test_tpl_id, user_a, test_proj_id))

            # Create test report for user_a
            test_rep_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO public.reports (id, project_id, user_id, template_id, title, status)
                VALUES (%s, %s, %s, %s, 'Final Thesis Report', 'draft');
            """, (test_rep_id, test_proj_id, user_a, test_tpl_id))

            # Create test report_version for user_a
            test_ver_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO public.report_versions (id, report_id, version_number, content_json)
                VALUES (%s, %s, 1, '{"abstract": "Top secret content"}'::jsonb);
            """, (test_ver_id, test_rep_id))

            # Now test as authenticated User B
            cur.execute("SET LOCAL ROLE authenticated;")
            cur.execute("SELECT set_config('request.jwt.claim.sub', %s, true);", (user_b,))

            # User B attempts to read User A's project
            cur.execute("SELECT * FROM public.projects WHERE id = %s;", (test_proj_id,))
            b_projects = cur.fetchall()
            print(f"User B query for User A's project returned: {len(b_projects)} rows (Expected: 0)")
            assert len(b_projects) == 0, "RLS FAILURE: User B was able to see User A's project!"

            # User B attempts to read User A's report
            cur.execute("SELECT * FROM public.reports WHERE id = %s;", (test_rep_id,))
            b_reports = cur.fetchall()
            print(f"User B query for User A's report returned: {len(b_reports)} rows (Expected: 0)")
            assert len(b_reports) == 0, "RLS FAILURE: User B was able to see User A's report!"

            # User B attempts to read User A's report_versions
            cur.execute("SELECT * FROM public.report_versions WHERE id = %s;", (test_ver_id,))
            b_versions = cur.fetchall()
            print(f"User B query for User A's report_versions returned: {len(b_versions)} rows (Expected: 0)")
            assert len(b_versions) == 0, "RLS FAILURE: User B was able to see User A's report version!"

            # Now switch context to User A
            cur.execute("SELECT set_config('request.jwt.claim.sub', %s, true);", (user_a,))
            cur.execute("SELECT * FROM public.projects WHERE id = %s;", (test_proj_id,))
            a_projects = cur.fetchall()
            print(f"User A query for own project returned: {len(a_projects)} rows (Expected: 1)")
            assert len(a_projects) == 1, "RLS FAILURE: User A could not see their own project!"

            # Clean up
            cur.execute("RESET ROLE;")
            cur.execute("DELETE FROM public.projects WHERE id = %s;", (test_proj_id,))
            print("[PASS] Cleaned up test isolation records!")

        print("\n=== ALL DATABASE FOUNDATION TESTS PASSED SUCCESSFULLY! ===")
        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"TEST FAILED: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    test_database_foundation()
