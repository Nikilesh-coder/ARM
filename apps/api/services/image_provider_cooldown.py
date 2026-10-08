"""
ARM Image Provider Cooldown and Health State Manager
====================================================
Tracks temporary provider health and rate limit / quota exhaustion states.
Implements ARM_IMAGE_PROVIDER_COOLDOWN_SECONDS (default 300 seconds).
Prevents repeated failing API calls to exhausted providers while safely
allowing re-probing after the cooldown period elapses.
"""

import os
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default cooldown duration: 300 seconds (5 minutes)
DEFAULT_COOLDOWN_SECONDS = 300


class ProviderHealthRecord:
    def __init__(self, name: str):
        self.name = name
        self.status = "AVAILABLE"  # AVAILABLE | COOLDOWN | EXHAUSTED | NOT_CONFIGURED
        self.last_failure_time: float = 0.0
        self.cooldown_duration: float = float(
            os.getenv("ARM_IMAGE_PROVIDER_COOLDOWN_SECONDS", DEFAULT_COOLDOWN_SECONDS)
        )
        self.failure_reason: Optional[str] = None
        self.failure_count: int = 0
        self.last_status_code: Optional[int] = None

    def is_in_cooldown(self) -> bool:
        if self.status != "COOLDOWN":
            return False
        elapsed = time.time() - self.last_failure_time
        if elapsed >= self.cooldown_duration:
            # Cooldown expired, restore to testing/available state
            logger.info(
                f"[ARM PROVIDER COOLDOWN] Cooldown expired ({elapsed:.1f}s >= {self.cooldown_duration}s) for {self.name}. Restoring to AVAILABLE."
            )
            self.status = "AVAILABLE"
            self.failure_reason = None
            return False
        return True

    def record_failure(self, reason: str, status_code: Optional[int] = None, is_exhausted: bool = False):
        self.last_failure_time = time.time()
        self.failure_reason = reason
        self.last_status_code = status_code
        self.failure_count += 1
        self.status = "COOLDOWN"
        default_dur = float(os.getenv("ARM_IMAGE_PROVIDER_COOLDOWN_SECONDS", DEFAULT_COOLDOWN_SECONDS))
        if is_exhausted or status_code in (402, 429):
            # Quota or credit exhaustion: persistent cooldown
            self.cooldown_duration = max(300.0, default_dur)
        elif status_code and 500 <= status_code < 600:
            # Temporary server error: 60s cooldown
            self.cooldown_duration = min(60.0, default_dur)
        else:
            self.cooldown_duration = default_dur

        logger.warning(
            f"[ARM PROVIDER HEALTH] Provider '{self.name}' entered COOLDOWN for {self.cooldown_duration}s. Reason: {reason} (Code: {status_code})"
        )

    def record_success(self):
        self.status = "AVAILABLE"
        self.failure_reason = None
        self.failure_count = 0
        self.last_status_code = 200

    def to_dict(self) -> Dict[str, Any]:
        in_cd = self.is_in_cooldown()
        remaining = max(0.0, self.cooldown_duration - (time.time() - self.last_failure_time)) if in_cd else 0.0
        return {
            "name": self.name,
            "status": self.status,
            "in_cooldown": in_cd,
            "cooldown_remaining_seconds": round(remaining, 1),
            "failure_count": self.failure_count,
            "failure_reason": self.failure_reason,
            "last_status_code": self.last_status_code,
        }

    def get_diagnostic(self) -> str:
        code_str = f"HTTP {self.last_status_code}" if self.last_status_code else "failed"
        reason_str = f": {self.failure_reason}" if self.failure_reason else ""
        return f"{self.name}: {code_str}{reason_str}"


class ImageProviderHealthManager:
    """Singleton health tracker for all ARM visual image providers."""

    _instance: Optional["ImageProviderHealthManager"] = None

    def __new__(cls) -> "ImageProviderHealthManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers = {}
        return cls._instance

    def _get_record(self, provider_name: str) -> ProviderHealthRecord:
        name_lower = provider_name.lower().strip()
        if name_lower not in self._providers:
            self._providers[name_lower] = ProviderHealthRecord(name_lower)
        return self._providers[name_lower]

    def is_available(self, provider_name: str) -> bool:
        record = self._get_record(provider_name)
        return not record.is_in_cooldown()

    def record_failure(
        self,
        provider_name: str,
        reason: str,
        status_code: Optional[int] = None,
        is_exhausted: bool = False,
    ):
        record = self._get_record(provider_name)
        record.record_failure(reason=reason, status_code=status_code, is_exhausted=is_exhausted)

    def record_success(self, provider_name: str):
        record = self._get_record(provider_name)
        record.record_success()

    def reset_cooldown(self, provider_name: Optional[str] = None):
        if provider_name:
            rec = self._get_record(provider_name)
            rec.status = "AVAILABLE"
            rec.failure_reason = None
            rec.failure_count = 0
        else:
            for rec in self._providers.values():
                rec.status = "AVAILABLE"
                rec.failure_reason = None
                rec.failure_count = 0

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        return {name: rec.to_dict() for name, rec in self._providers.items()}


# Singleton instance
image_provider_health_manager = ImageProviderHealthManager()
