"""
Production Verification Test: Zero-Change Real Report Generation Flow
Validates that when zero changes are requested (or zero replacements requested):
1. The production report-generation flow returns an exact raw copy of the selected template.
2. The downloaded DOCX is 100% byte-for-byte identical to the original uploaded template.
3. Original SHA-256 == Downloaded SHA-256.
4. Original file size == Downloaded file size.
"""

import os
import hashlib
import json
import urllib.request

BASE_URL = "http://127.0.0.1:8000"

# Original uploaded file on disk
ORIGINAL_PATH = os.path.abspath(
    r"C:\Users\A9959\OneDrive\Desktop\ARM\.storage\templates\users\1b2f3346-ca7f-4b38-916e-a3cb62a6e9cd\templates\tpl_cust_140ada3976a8\JAGADEESH PPT.docx"
)

def post_json(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return resp.getcode(), json.loads(resp.read().decode("utf-8"))

def get_bytes(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return resp.getcode(), resp.read()

def test_zero_change_report_generation():
    assert os.path.exists(ORIGINAL_PATH), f"Original template not found at {ORIGINAL_PATH}"
    with open(ORIGINAL_PATH, "rb") as f:
        orig_bytes = f.read()
    orig_sha256 = hashlib.sha256(orig_bytes).hexdigest()
    orig_size = len(orig_bytes)

    print(f"\n--- [ORIGINAL UPLOADED TEMPLATE] ---")
    print(f"Path: {ORIGINAL_PATH}")
    print(f"Size: {orig_size} bytes")
    print(f"SHA-256: {orig_sha256}")

    # TEST 1: User specifies template_id and explicitly asks zero changes
    print(f"\n--- [TEST 1: POST /api/v1/reports/generate with template_id] ---")
    payload1 = {
        "title": "Do not change anything. Return the template exactly as uploaded.",
        "problem_statement": "Do not change anything. Return the template exactly as uploaded.",
        "template_id": "tpl_cust_140ada3976a8"
    }
    status1, data1 = post_json(f"{BASE_URL}/api/v1/reports/generate", payload1)
    assert status1 == 200, f"Generate failed: {status1} {data1}"
    report_id1 = data1["report_id"]
    print(f"Report generated: ID={report_id1}, file_size={data1.get('file_size_bytes')}")

    # Download report via production download endpoint
    dl_status1, dl_bytes1 = get_bytes(f"{BASE_URL}/api/v1/reports/{report_id1}/download")
    assert dl_status1 == 200, f"Download failed: {dl_status1}"
    dl_sha256_1 = hashlib.sha256(dl_bytes1).hexdigest()
    dl_size1 = len(dl_bytes1)

    print(f"Downloaded Size: {dl_size1} bytes")
    print(f"Downloaded SHA-256: {dl_sha256_1}")
    print(f"Sizes match: {orig_size == dl_size1}")
    print(f"SHA-256 match: {orig_sha256 == dl_sha256_1}")
    assert orig_sha256 == dl_sha256_1, "TEST 1 FAILED: Hashes do not match byte-for-byte!"
    assert orig_size == dl_size1, "TEST 1 FAILED: Sizes do not match!"
    print(">>> TEST 1 PASSED: 100% BYTE-FOR-BYTE IDENTICAL!")

    # TEST 2: User doesn't pass template_id in payload, but active template is resolved
    print(f"\n--- [TEST 2: POST /api/v1/reports/generate with resolved active template] ---")
    payload2 = {
        "title": "Do not change anything. Return the template exactly as uploaded.",
        "problem_statement": "Do not change anything. Return the template exactly as uploaded.",
        "template_id": None
    }
    status2, data2 = post_json(f"{BASE_URL}/api/v1/reports/generate", payload2)
    assert status2 == 200, f"Generate failed: {status2} {data2}"
    report_id2 = data2["report_id"]
    print(f"Report generated: ID={report_id2}, file_size={data2.get('file_size_bytes')}")

    dl_status2, dl_bytes2 = get_bytes(f"{BASE_URL}/api/v1/reports/{report_id2}/download")
    assert dl_status2 == 200, f"Download failed: {dl_status2}"
    dl_sha256_2 = hashlib.sha256(dl_bytes2).hexdigest()
    dl_size2 = len(dl_bytes2)

    print(f"Downloaded Size: {dl_size2} bytes")
    print(f"Downloaded SHA-256: {dl_sha256_2}")
    print(f"Sizes match: {orig_size == dl_size2}")
    print(f"SHA-256 match: {orig_sha256 == dl_sha256_2}")
    assert orig_sha256 == dl_sha256_2, "TEST 2 FAILED: Hashes do not match byte-for-byte!"
    assert orig_size == dl_size2, "TEST 2 FAILED: Sizes do not match!"
    print(">>> TEST 2 PASSED: 100% BYTE-FOR-BYTE IDENTICAL!")

    print("\n=======================================================")
    print("ALL PRODUCTION ZERO-CHANGE REPORT FLOW TESTS PASSED 100%!")
    print("=======================================================")

if __name__ == "__main__":
    test_zero_change_report_generation()
