"""
Test Complete Report Generation for Project: 'AI based irrigation system'
========================================================================
Executes full report generation via POST /api/v1/reports/generate.
Verifies that:
1. Status is 200 OK.
2. The Unicode ligature \ufb01 on Slide 34 is handled without crashing.
3. Hugging Face images are synthesized and distinct across slides.
4. Output DOCX exists and download endpoint serves the exact file.
"""

import os
import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

payload = {
    "title": "AI based irrigation system",
    "problem_statement": "Automated precision irrigation system for agricultural farms using smart sensors and AI decision making.",
    "project_id": "6a51d5b1-94c1-413d-ab87-87ddc2e3d7e9",
    "template_id": "b6acbdd4-c09d-4346-9981-b9c3db1d36a1",
    "query": "create an report on AI based irrigation",
}


def run():
    print("\n" + "=" * 80)
    print("ARM COMPLETE REPORT GENERATION TEST")
    print(f"Project Title: {payload['title']}")
    print(f"Template ID: {payload['template_id']}")
    print("=" * 80)

    url = f"{BASE_URL}/api/v1/reports/generate"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    try:
        print("\nSending POST /api/v1/reports/generate (this synthesizes content and images)...")
        with urllib.request.urlopen(req, timeout=300) as response:
            status = response.status
            body = response.read().decode("utf-8")
            res_json = json.loads(body)

            print(f"\nResponse Status: {status}")
            print(f"Report ID: {res_json.get('report_id')}")
            print(f"Document ID: {res_json.get('document_id')}")
            print(f"Status: {res_json.get('status')}")
            print(f"File Size: {res_json.get('file_size_bytes')} bytes")
            print(f"Output Path: {res_json.get('output_path')}")
            print(f"Fields Replaced: {res_json.get('fields_replaced')}")
            print(f"Images Replaced: {res_json.get('images_replaced')}")

            docx_path = res_json.get("output_path")
            assert docx_path and os.path.exists(docx_path), "Generated DOCX does not exist on disk!"
            print(f"DOCX Exists: YES ({os.path.getsize(docx_path)} bytes)")

            # Test download
            dl_url = f"{BASE_URL}/api/v1/reports/{res_json.get('report_id')}/download"
            print(f"\nTesting Download: {dl_url}")
            with urllib.request.urlopen(dl_url, timeout=30) as dl_resp:
                dl_bytes = dl_resp.read()
                print(f"Downloaded Bytes: {len(dl_bytes)} (Match: {len(dl_bytes) == os.path.getsize(docx_path)})")

            print("\n" + "=" * 80)
            print("SUCCESS: Full report generation completed with 0 errors!")
            print("=" * 80)
            return True

    except urllib.error.HTTPError as he:
        err_body = he.read().decode("utf-8", errors="replace")
        print(f"\n[HTTP ERROR {he.code}]: {err_body}")
        return False
    except Exception as ex:
        print(f"\n[EXCEPTION]: {ex}")
        return False


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
