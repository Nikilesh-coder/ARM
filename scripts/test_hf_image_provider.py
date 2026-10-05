"""
ARM Hugging Face Inference Providers Diagnostic Test
====================================================
Generates exactly 3 diagnostic images using Hugging Face Inference Providers:
1. Smart AI-powered irrigation system in agricultural field
2. Close-up of digital soil moisture sensor probe in soil
3. Drought-stressed agricultural field with dry cracked soil

Prints required diagnostic info and verifies:
Image 1 SHA != Image 2 SHA != Image 3 SHA
"""

import os
import sys
import hashlib
from typing import List, Dict

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from apps.api.core.config import settings
from apps.api.services.hf_image_provider import HFImageProvider


TEST_PROMPTS = [
    {
        "id": 1,
        "name": "IMAGE 1",
        "prompt": "Realistic agricultural field using a smart AI-powered irrigation system, healthy green crops, visible irrigation pipes and water-efficient farming technology, natural realistic photography",
    },
    {
        "id": 2,
        "name": "IMAGE 2",
        "prompt": "Close-up of a digital soil moisture sensor probe inserted into rich farm soil near crop roots, modern agricultural IoT sensor device, realistic high detail photography",
    },
    {
        "id": 3,
        "name": "IMAGE 3",
        "prompt": "Drought-stressed agricultural field suffering from water scarcity, dry cracked soil and wilted crops, dramatic realistic photography",
    },
]


def run_test():
    print("\n" + "=" * 80)
    print("ARM HUGGING FACE INFERENCE PROVIDER 3-IMAGE DIAGNOSTIC TEST")
    print("=" * 80)

    # 1. Check HF_TOKEN
    token = HFImageProvider.get_token()
    if not token:
        print("\n[ERROR] HF_TOKEN is NOT configured in .env or environment!")
        print("Please add a valid Hugging Face Access Token to .env:")
        print("HF_TOKEN=hf_...")
        print("=" * 80)
        return False

    print("\nHF_TOKEN Status: CONFIGURED (Token value is securely masked)")

    # 2. Query available models dynamically
    print("\nQuerying Hugging Face API for pipeline_tag=text-to-image...")
    models = HFImageProvider.query_available_models(limit=5)
    print(f"Top available text-to-image models on Hugging Face: {models}")
    print(f"Selected default model: {settings.image_provider.hf_image_model}")

    output_dir = os.path.abspath(os.path.join("generated_images", "hf_diagnostic_test"))
    os.makedirs(output_dir, exist_ok=True)

    results = []
    shas = []

    for item in TEST_PROMPTS:
        img_id = item["id"]
        img_name = item["name"]
        prompt = item["prompt"]

        print(f"\n--- GENERATING {img_name} ---")
        print(f"Prompt: {prompt}")

        res = HFImageProvider.generate_image(prompt=prompt)
        if not res:
            print(f"[FAIL] Image generation failed for {img_name}!")
            return False

        # Save to disk
        out_filename = f"hf_diag_image_{img_id}.png"
        out_filepath = os.path.join(output_dir, out_filename)
        with open(out_filepath, "wb") as f:
            f.write(res.image_bytes)

        # Re-verify SHA256 from disk
        with open(out_filepath, "rb") as f:
            disk_sha = hashlib.sha256(f.read()).hexdigest()

        # PRINT MANDATORY DIAGNOSTIC BLOCK
        print("\n" + "-" * 50)
        print(f"{img_name} RESULT:")
        print(f"Provider name: {res.provider_name}")
        print(f"Model name: {res.model_name}")
        print(f"HTTP status: {res.http_status}")
        print(f"Response type: {res.response_type}")
        print(f"Image byte count: {len(res.image_bytes)} bytes")
        print(f"Image dimensions: {res.dimensions[0]}x{res.dimensions[1]}")
        print(f"Saved file path: {out_filepath}")
        print(f"SHA-256 hash: {disk_sha}")
        print("-" * 50)

        results.append({
            "name": img_name,
            "sha": disk_sha,
            "bytes": len(res.image_bytes),
            "path": out_filepath,
        })
        shas.append(disk_sha)

    # VERIFY UNIQUENESS
    print("\n" + "=" * 80)
    print("VERIFYING UNIQUENESS (SHA-256 COLLISION CHECK)")
    print("=" * 80)
    sha1 = shas[0]
    sha2 = shas[1]
    sha3 = shas[2]

    print(f"Image 1 SHA-256: {sha1}")
    print(f"Image 2 SHA-256: {sha2}")
    print(f"Image 3 SHA-256: {sha3}")

    unique_count = len(set(shas))
    if unique_count == 3:
        print("\nSUCCESS: Image 1 SHA != Image 2 SHA != Image 3 SHA (All 3 images are 100% unique!)")
        print("=" * 80 + "\n")
        return True
    else:
        print(f"\nFAILURE: Duplicate SHA detected! Unique count = {unique_count}/3")
        print("=" * 80 + "\n")
        return False


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
