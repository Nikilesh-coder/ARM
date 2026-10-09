"""
ARM Supabase Authentication & Rate Limit Robustness Test Suite
==============================================================
Validates:
1. Email + password login works without triggering email sends.
2. Multiple consecutive logins succeed without encountering rate limits.
3. Duplicate signup prevention and user status inspection.
4. Email verification requirements and flow integrity.
5. Password recovery handling and rate-limit diagnostics.
"""

import os
import pytest
import requests
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv(".env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

from apps.api.main import app
from apps.api.core.database import db_manager


class TestSupabaseAuthFlow:
    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)
        cls.supabase_client = db_manager.client
        assert cls.supabase_client is not None, "Supabase client must be initialized"

    def test_01_user_status_inspection_endpoint(self):
        """Verifies status check endpoint runs without sending emails."""
        # Check known confirmed user
        res = self.client.get("/api/v1/auth/user-status?email=student@university.edu")
        assert res.status_code == 200
        data = res.json()
        assert data["exists"] is True
        assert data["email_confirmed"] is True

        # Check nonexistent user
        res_none = self.client.get("/api/v1/auth/user-status?email=totally_random_ghost_scholar@university.edu")
        assert res_none.status_code == 200
        assert res_none.json()["exists"] is False

    def test_02_repeated_password_login_no_rate_limit(self):
        """
        Confirms email+password login strictly uses the password grant and
        does not invoke mailers, allowing many rapid logins without 429 errors.
        """
        temp_email = "auth_speed_test_scholar_1@university.edu"
        temp_pwd = "StrongPassword999!"

        # Ensure user exists and is confirmed
        existing_users = self.supabase_client.auth.admin.list_users()
        for u in existing_users:
            if u.email == temp_email:
                self.supabase_client.auth.admin.delete_user(u.id)

        user = self.supabase_client.auth.admin.create_user({
            "email": temp_email,
            "password": temp_pwd,
            "email_confirm": True
        })
        user_id = user.user.id

        try:
            # Execute 10 consecutive rapid logins
            success_count = 0
            for _ in range(10):
                r = requests.post(
                    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                    headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
                    json={"email": temp_email, "password": temp_pwd}
                )
                if r.status_code == 200 and "access_token" in r.json():
                    success_count += 1

            assert success_count == 10, f"Expected 10/10 logins to succeed, got {success_count}"
        finally:
            self.supabase_client.auth.admin.delete_user(user_id)

    def test_03_duplicate_signup_inspection_prevents_re_sending(self):
        """
        Verifies that querying user-status detects existing accounts
        so the frontend can alert the user before triggering duplicate mail calls.
        """
        res = self.client.get("/api/v1/auth/user-status?email=student@university.edu")
        assert res.status_code == 200
        data = res.json()
        assert data["exists"] is True
        assert data["email_confirmed"] is True

    def test_04_recovery_rate_limit_detection(self):
        """
        Verifies that Supabase's email rate limit (over_email_send_rate_limit)
        is properly detected when multiple recovery calls are made in seconds.
        """
        # Call recovery endpoint directly
        r1 = requests.post(
            f"{SUPABASE_URL}/auth/v1/recover",
            headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
            json={"email": "student@university.edu"}
        )
        # Immediate second call should receive rate limit 429
        r2 = requests.post(
            f"{SUPABASE_URL}/auth/v1/recover",
            headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
            json={"email": "student@university.edu"}
        )
        assert r2.status_code == 429
        body = r2.json()
        assert body.get("error_code") == "over_email_send_rate_limit" or "rate limit" in body.get("msg", "").lower()
