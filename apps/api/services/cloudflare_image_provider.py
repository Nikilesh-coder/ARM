"""
ARM Cloudflare Image Provider Bridge
====================================
Maintains seamless backwards compatibility by wrapping CloudflareWorkerImageProvider.
"""

from apps.api.services.cloudflare_worker_image_provider import (
    CloudflareWorkerImageProvider,
    CloudflareWorkerImageGenerationResult,
)

# Export aliases for seamless backwards-compatibility
CloudflareImageProvider = CloudflareWorkerImageProvider
CloudflareImageGenerationResult = CloudflareWorkerImageGenerationResult

__all__ = [
    "CloudflareWorkerImageProvider",
    "CloudflareWorkerImageGenerationResult",
    "CloudflareImageProvider",
    "CloudflareImageGenerationResult",
]
