import os
import sys
from dotenv import load_dotenv

# Load local .env
load_dotenv(".env")
sys.path.insert(0, os.path.abspath("."))

from apps.api.services.xkiro_image_provider import XKiroImageProvider
from apps.api.services.cloudflare_worker_image_provider import CloudflareWorkerImageProvider
from apps.api.services.cloudflare_image_provider import CloudflareImageProvider
from apps.api.services.hf_image_provider import HFImageProvider
from apps.api.services.together_image_provider import TogetherImageProvider
from apps.api.services.local_rtx_provider import LocalRTXProvider
from apps.api.services.image_provider_cooldown import image_provider_health_manager

print("=== IMAGE PROVIDER CONFIGURATION DIAGNOSTICS ===")
print("XKIRO_API_KEY set:", bool(os.getenv("XKIRO_API_KEY")))
print("XKiro configured:", XKiroImageProvider.is_configured())
print("XKiro base_url:", XKiroImageProvider.get_base_url())
print("XKiro model:", XKiroImageProvider.get_model_name())

print("\nCLOUDFLARE_WORKER_API_KEY set:", bool(os.getenv("CLOUDFLARE_WORKER_API_KEY")))
print("CloudflareWorker configured:", CloudflareWorkerImageProvider.is_configured())
print("CloudflareWorker url:", CloudflareWorkerImageProvider.get_worker_url())

print("\nCLOUDFLARE_API_TOKEN set:", bool(os.getenv("CLOUDFLARE_API_TOKEN")))
print("CloudflareDirect configured:", CloudflareImageProvider.is_configured())

print("\nHF_TOKEN set:", bool(os.getenv("HF_TOKEN")))
print("HF configured:", HFImageProvider.is_configured())

print("\nTOGETHER_API_KEY set:", bool(os.getenv("TOGETHER_API_KEY")))
print("Together configured:", TogetherImageProvider.is_configured())

print("\nLOCAL_RTX_ENABLED:", os.getenv("LOCAL_RTX_ENABLED"))
print("LocalRTX enabled:", LocalRTXProvider.is_enabled())

print("\n=== ATTEMPTING LIVE PROVIDER CALLS ===")
prompt = "High-tech smart agricultural drip irrigation system with IoT soil moisture sensors in agricultural field, professional photography"

# 1. Supernova / xKiro
if XKiroImageProvider.is_configured():
    print("\n--- Testing Supernova (xKiro) ---")
    try:
        quota_ok, quota_msg = XKiroImageProvider.check_free_quota()
        print(f"xKiro free quota check: ok={quota_ok}, msg={quota_msg}")
        res = XKiroImageProvider.generate_image(prompt)
        print(f"xKiro result: {res}")
        if res:
            print(f"xKiro bytes: {len(res.image_bytes)}, dims: {res.dimensions}")
    except Exception as e:
        print(f"xKiro exception: {e}")
else:
    print("\nxKiro is NOT configured (missing XKIRO_API_KEY)")

# 2. Cloudflare Worker
if CloudflareWorkerImageProvider.is_configured():
    print("\n--- Testing Cloudflare Worker ---")
    try:
        res = CloudflareWorkerImageProvider.generate_image(prompt)
        print(f"Cloudflare Worker result: {res}")
        if res:
            print(f"Cloudflare Worker bytes: {len(res.image_bytes)}, dims: {res.dimensions}")
    except Exception as e:
        print(f"Cloudflare Worker exception: {e}")
else:
    print("\nCloudflare Worker is NOT configured (missing CLOUDFLARE_WORKER_API_KEY)")

# 3. Cloudflare Direct
if CloudflareImageProvider.is_configured():
    print("\n--- Testing Cloudflare Direct ---")
    try:
        res = CloudflareImageProvider.generate_image(prompt)
        print(f"Cloudflare Direct result: {res}")
        if res:
            print(f"Cloudflare Direct bytes: {len(res.image_bytes)}")
    except Exception as e:
        print(f"Cloudflare Direct exception: {e}")
else:
    print("\nCloudflare Direct is NOT configured")

# 4. HF
if HFImageProvider.is_configured():
    print("\n--- Testing Hugging Face ---")
    try:
        res = HFImageProvider.generate_image(prompt)
        print(f"HF result: {res}")
    except Exception as e:
        print(f"HF exception: {e}")
else:
    print("\nHF is NOT configured (missing HF_TOKEN)")

# 5. Together
if TogetherImageProvider.is_configured():
    print("\n--- Testing Together AI ---")
    try:
        res = TogetherImageProvider.generate_image(prompt)
        print(f"Together result: {res}")
    except Exception as e:
        print(f"Together exception: {e}")
else:
    print("\nTogether is NOT configured (missing TOGETHER_API_KEY)")
