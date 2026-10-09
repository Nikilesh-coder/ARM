"""
ARM Supabase Authentication Router
===================================
Provides scalable authentication assistance, status inspection, and admin-assisted
verification without exhausting Supabase's built-in email rate limits.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status, Query
from apps.api.core.database import db_manager
from apps.api.core.logging import get_logger

logger = get_logger("auth_router")

router = APIRouter(prefix="/auth", tags=["Authentication"])


class ConfirmEmailRequest(BaseModel):
    email: str


class GenerateActionLinkRequest(BaseModel):
    email: str
    action_type: str = "signup"  # "signup" | "recovery" | "magiclink"


class ResetPasswordDirectRequest(BaseModel):
    email: str
    new_password: str


@router.get("/user-status")
async def get_user_status(email: str = Query(..., description="Academic email address to inspect")):
    """
    Inspects user verification status and profile without sending any email.
    Prevents duplicate signups and blind confirmation resends.
    """
    client = db_manager.client
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database foundation unavailable"
        )

    clean_email = email.strip().lower()

    try:
        users = client.auth.admin.list_users()
        target_user = None
        for u in users:
            if getattr(u, "email", "").lower() == clean_email:
                target_user = u
                break

        if not target_user:
            return {
                "exists": False,
                "email": clean_email,
                "email_confirmed": False,
                "message": "User not found"
            }

        is_confirmed = bool(getattr(target_user, "email_confirmed_at", None))
        return {
            "exists": True,
            "id": getattr(target_user, "id", None),
            "email": clean_email,
            "email_confirmed": is_confirmed,
            "created_at": getattr(target_user, "created_at", None),
            "last_sign_in_at": getattr(target_user, "last_sign_in_at", None),
            "metadata": getattr(target_user, "user_metadata", {}) or {}
        }
    except Exception as e:
        logger.error(f"[Auth] Error checking user status for {clean_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inspecting auth status: {str(e)}"
        )


@router.post("/confirm-email")
async def confirm_email_directly(req: ConfirmEmailRequest):
    """
    Directly marks an unconfirmed user's email as confirmed via Supabase Admin API.
    Bypasses the built-in email rate limit (3 emails/hour) for testing or emergency user activation.
    Preserves existing user IDs, profiles, and database relationships.
    """
    client = db_manager.client
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database foundation unavailable"
        )

    clean_email = req.email.strip().lower()

    try:
        users = client.auth.admin.list_users()
        target_user = None
        for u in users:
            if getattr(u, "email", "").lower() == clean_email:
                target_user = u
                break

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email '{clean_email}' not found."
            )

        user_id = getattr(target_user, "id", None)
        # Update user to confirmed
        client.auth.admin.update_user_by_id(user_id, {"email_confirm": True})
        logger.info(f"[Auth] Successfully verified email directly for user {clean_email} ({user_id})")

        return {
            "success": True,
            "id": user_id,
            "email": clean_email,
            "email_confirmed": True,
            "message": "User email successfully confirmed directly."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Auth] Error directly confirming email for {clean_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm email: {str(e)}"
        )


@router.post("/generate-action-link")
async def generate_action_link(req: GenerateActionLinkRequest):
    """
    Generates a secure verification or recovery action link using Supabase Admin API
    WITHOUT sending an email through Supabase's rate-limited mailer.
    """
    client = db_manager.client
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database foundation unavailable"
        )

    clean_email = req.email.strip().lower()

    try:
        link_type = req.action_type.strip().lower()
        if link_type not in ("signup", "recovery", "magiclink", "invite"):
            link_type = "signup"

        link_response = client.auth.admin.generate_link({
            "type": link_type,
            "email": clean_email,
        })

        action_link = None
        if hasattr(link_response, "properties"):
            action_link = getattr(link_response.properties, "action_link", None)
        elif isinstance(link_response, dict):
            action_link = link_response.get("action_link")

        return {
            "success": True,
            "email": clean_email,
            "type": link_type,
            "action_link": action_link,
            "message": "Action link generated without consuming mailer quota."
        }
    except Exception as e:
        logger.error(f"[Auth] Error generating action link for {clean_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate action link: {str(e)}"
        )
