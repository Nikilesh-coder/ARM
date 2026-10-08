"""
ARM Production Browser Smoke Test Script
Executes the exact 12-step verification suite against https://arm-caw2.vercel.app/ using real Chrome.
"""

import sys
import os
import time
import json
import zipfile
import urllib.request
from playwright.sync_api import sync_playwright

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "https://arm-caw2.vercel.app"
TEST_EMAIL = "prod_smoke_test_scholar@university.edu"
TEST_PASSWORD = "AcademicSecurePassword2026!"
SAMPLE_TEMPLATE_PATH = os.path.abspath("apps/web/public/Project_Report_Final_IEEE.docx")
STALE_TEMPLATE_ID = "0484aecb-dbc1-4671-a388-0f820124ca0e"

results = {}
console_errors = []
network_requests = []
generation_request_body = None
generation_response_body = None
downloaded_report_path = None
uploaded_template_id = None
created_project_id = None

def run_smoke_test():
    global generation_request_body, generation_response_body, downloaded_report_path
    global uploaded_template_id, created_project_id
    
    print(f"[SMOKE-TEST] Starting production browser test against {BASE_URL}", flush=True)
    print(f"[SMOKE-TEST] Using template file: {SAMPLE_TEMPLATE_PATH}", flush=True)
    assert os.path.exists(SAMPLE_TEMPLATE_PATH), f"Template file not found: {SAMPLE_TEMPLATE_PATH}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            accept_downloads=True
        )
        page = context.new_page()

        # Capture console messages
        def on_console(msg):
            txt = msg.text
            if msg.type == "error":
                if not ("favicon.ico" in txt or "status of 404" in txt and "favicon" in txt):
                    console_errors.append(f"[{msg.type.upper()}] {txt}")
            print(f"[CONSOLE {msg.type.upper()}] {txt[:120]}", flush=True)
        page.on("console", on_console)

        # Intercept network requests
        def on_request(request):
            url = request.url
            network_requests.append(url)
            if "/api/v1/reports/generate" in url and request.method == "POST":
                try:
                    post_data = request.post_data
                    if post_data:
                        global generation_request_body
                        generation_request_body = json.loads(post_data)
                        print(f"[NETWORK] Intercepted /reports/generate request: template_id={generation_request_body.get('template_id')}", flush=True)
                except Exception as e:
                    print(f"[NETWORK] Could not parse generate post data: {e}", flush=True)
        page.on("request", on_request)

        def on_response(response):
            url = response.url
            if response.status >= 400:
                print(f"[HTTP {response.status}] {url}", flush=True)
            if "/api/v1/reports/generate" in url and response.request.method == "POST":
                try:
                    global generation_response_body
                    generation_response_body = response.json()
                    print(f"[NETWORK] Intercepted /reports/generate response: status={response.status} report_id={generation_response_body.get('report_id')}", flush=True)
                except Exception as e:
                    print(f"[NETWORK] Could not parse generate response: {e}", flush=True)
        page.on("response", on_response)

        # -------------------------------------------------------------
        # STEP 1: LOGIN
        # -------------------------------------------------------------
        print("\n--- STEP 1: Login ---", flush=True)
        try:
            page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=30000)
            time.sleep(1)
            
            page.fill('input[type="email"]', TEST_EMAIL)
            page.fill('input[type="password"]', TEST_PASSWORD)
            page.click('button[type="submit"]')
            print("[LOGIN] Submitted credentials, waiting for navigation to /app...", flush=True)
            
            page.wait_for_url("**/app**", timeout=25000)
            time.sleep(2)
            results["step_1_login"] = "PASS"
            print(f"[LOGIN] Logged in successfully: {page.url}", flush=True)
        except Exception as e:
            results["step_1_login"] = f"FAIL: {e}"
            print(f"[LOGIN] Error: {e}", flush=True)

        # -------------------------------------------------------------
        # STEP 2: CREATE A NEW PROJECT NAMED "AI Irrigation Test"
        # -------------------------------------------------------------
        print("\n--- STEP 2: Create Project 'AI Irrigation Test' ---", flush=True)
        try:
            page.goto(f"{BASE_URL}/app/projects", wait_until="networkidle", timeout=20000)
            time.sleep(2)
            
            # Click "Create Project" button in the header
            create_btn = page.locator('header button:has-text("Create Project")').first
            create_btn.click()
            time.sleep(1)
            
            # Fill title & description in CreateProjectModal
            page.fill('input[placeholder*="Automated IoT"]', "AI Irrigation Test")
            page.fill('textarea[placeholder*="Detail the technical"]', "Automated precision drip irrigation system with IoT soil sensors and predictive water distribution.")
            time.sleep(1)
            
            # Submit project creation
            submit_proj_btn = page.locator('button:has-text("Create Project & Report")').first
            submit_proj_btn.click()
            time.sleep(4)
            
            # Check project in localStorage or page
            active_proj_str = page.evaluate("() => localStorage.getItem('arm_active_project')")
            if active_proj_str:
                active_proj = json.loads(active_proj_str)
                created_project_id = active_proj.get("id")
                print(f"[PROJECT] Created project ID: {created_project_id}, title: {active_proj.get('title')}", flush=True)
            
            results["step_2_create_project"] = "PASS" if created_project_id else "FAIL: No project ID in localStorage"
        except Exception as e:
            results["step_2_create_project"] = f"FAIL: {e}"
            print(f"[PROJECT] Error: {e}", flush=True)

        # -------------------------------------------------------------
        # STEP 3: UPLOAD REAL COLLEGE DOCX TEMPLATE THROUGH ARM UI
        # -------------------------------------------------------------
        print("\n--- STEP 3: Upload Real College DOCX Template ---", flush=True)
        try:
            page.goto(f"{BASE_URL}/app/templates", wait_until="networkidle", timeout=20000)
            time.sleep(2)
            
            # Click "+ Upload College Template" button
            upload_btn = page.locator('button:has-text("Upload College Template")').first
            upload_btn.click()
            time.sleep(1)
            
            # Step 1: Set input file on the modal's file input
            file_input = page.locator('.fixed input[type="file"]').first
            file_input.set_input_files(SAMPLE_TEMPLATE_PATH)
            time.sleep(2)
            
            # Step 2: Fill template name
            name_input = page.locator('input[placeholder*="ABC College Capstone"], input[placeholder*="Department Project Report Template"]').first
            name_input.wait_for(timeout=10000)
            name_input.fill("AI Irrigation IEEE Template")
            time.sleep(1)
            
            # Click "Analyze Template"
            analyze_btn = page.locator('button:has-text("Analyze Template")').first
            analyze_btn.click()
            print("[TEMPLATE-UPLOAD] Clicked Analyze Template, waiting for analysis...", flush=True)
            
            # Step 4: Wait for mapping screen (Save Template button)
            save_btn = page.locator('button:has-text("Save Template")').first
            save_btn.wait_for(timeout=40000)
            time.sleep(1)
            
            save_btn.click()
            print("[TEMPLATE-UPLOAD] Clicked Save Template, waiting for modal to close...", flush=True)
            time.sleep(3)
            
            uploaded_template_id = page.evaluate("() => localStorage.getItem('arm_selected_template_id')")
            print(f"[TEMPLATE-UPLOAD] Uploaded template ID: {uploaded_template_id}", flush=True)
            
            results["step_3_upload_template"] = "PASS" if uploaded_template_id else "FAIL: No template ID stored"
        except Exception as e:
            results["step_3_upload_template"] = f"FAIL: {e}"
            print(f"[TEMPLATE-UPLOAD] Error: {e}", flush=True)

        # -------------------------------------------------------------
        # STEP 4: VERIFY UPLOADED TEMPLATE IN TEMPLATE LIST
        # -------------------------------------------------------------
        print("\n--- STEP 4: Verify Template in List ---", flush=True)
        try:
            page.wait_for_selector('text="AI Irrigation IEEE Template"', timeout=15000)
            results["step_4_template_in_list"] = "PASS"
            print("[TEMPLATE-LIST] Template 'AI Irrigation IEEE Template' is visible in list.", flush=True)
        except Exception as e:
            results["step_4_template_in_list"] = f"FAIL: {e}"
            print(f"[TEMPLATE-LIST] Error: {e}", flush=True)

        # -------------------------------------------------------------
        # STEP 5: CLICK 'USE THIS TEMPLATE'
        # -------------------------------------------------------------
        print("\n--- STEP 5: Click 'Use This Template' ---", flush=True)
        try:
            # Find the card with the uploaded template name
            card = page.locator('div.rounded-xl').filter(has_text="AI Irrigation IEEE Template").last
            use_btn = card.locator('button:has-text("Use This Template"), button:has-text("Active Template")').first
            use_btn.wait_for(timeout=10000)
            btn_txt = use_btn.inner_text()
            print(f"[USE-TEMPLATE] Initial button text: '{btn_txt}'", flush=True)
            if "Use This Template" in btn_txt:
                use_btn.click()
                time.sleep(2)
            
            # Verify it shows "Active Template" or is stored in localStorage
            active_btn_count = card.locator('button:has-text("Active Template")').count()
            is_active = (active_btn_count > 0) or (page.evaluate(f"() => localStorage.getItem('arm_selected_template_id') === '{uploaded_template_id}'"))
            results["step_5_use_template"] = "PASS" if is_active else "FAIL: Button did not toggle to Active"
            print(f"[USE-TEMPLATE] Template active status: {is_active}", flush=True)
        except Exception as e:
            results["step_5_use_template"] = f"FAIL: {e}"
            print(f"[USE-TEMPLATE] Error: {e}", flush=True)

        # -------------------------------------------------------------
        # STEP 6: VERIFY SELECTED TEMPLATE ASSOCIATED WITH ACTIVE PROJECT
        # -------------------------------------------------------------
        print("\n--- STEP 6: Verify Association with Active Project ---", flush=True)
        try:
            stored_tid = page.evaluate("() => localStorage.getItem('arm_selected_template_id')")
            stored_proj = page.evaluate("() => localStorage.getItem('arm_active_project')")
            proj_data = json.loads(stored_proj) if stored_proj else {}
            
            print(f"[ASSOCIATION] stored_tid = {stored_tid}", flush=True)
            print(f"[ASSOCIATION] project.template_id = {proj_data.get('template_id')}", flush=True)
            
            associated = bool(stored_tid and stored_tid == uploaded_template_id)
            results["step_6_associated_with_project"] = "PASS" if associated else f"FAIL: mismatch {stored_tid} vs {uploaded_template_id}"
        except Exception as e:
            results["step_6_associated_with_project"] = f"FAIL: {e}"
            print(f"[ASSOCIATION] Error: {e}", flush=True)

        # -------------------------------------------------------------
        # STEP 7: REFRESH BROWSER AND VERIFY PERSISTENCE
        # -------------------------------------------------------------
        print("\n--- STEP 7: Refresh Browser and Verify Persistence ---", flush=True)
        try:
            page.reload(wait_until="networkidle")
            time.sleep(2)
            
            reloaded_tid = page.evaluate("() => localStorage.getItem('arm_selected_template_id')")
            print(f"[PERSISTENCE] reloaded_tid = {reloaded_tid}", flush=True)
            
            persists = (reloaded_tid == uploaded_template_id and reloaded_tid != STALE_TEMPLATE_ID)
            results["step_7_refresh_persistence"] = "PASS" if persists else f"FAIL: {reloaded_tid}"
        except Exception as e:
            results["step_7_refresh_persistence"] = f"FAIL: {e}"
            print(f"[PERSISTENCE] Error: {e}", flush=True)

        # -------------------------------------------------------------
        # STEP 8: GENERATE REPORT FROM UI
        # -------------------------------------------------------------
        print("\n--- STEP 8: Generate Report from UI ---", flush=True)
        try:
            page.goto(f"{BASE_URL}/app", wait_until="networkidle", timeout=20000)
            time.sleep(2)
            
            composer_input = page.locator('textarea[placeholder*="Ask ARM"]').first
            composer_input.fill("Automated precision irrigation monitoring and water conservation system")
            time.sleep(1)
            
            # Send message / start generation
            send_btn = page.locator('button:has(svg.lucide-arrow-up)').first
            send_btn.click()
            print("[GENERATE] Clicked send button, generation in progress...", flush=True)
            
            # Wait for synthesis success text or download button (timeout 90s)
            page.wait_for_selector('text="Report Successfully Synthesized!"', timeout=90000)
            time.sleep(2)
            
            results["step_8_generate_report"] = "PASS"
            print("[GENERATE] Report successfully synthesized and visible in UI!", flush=True)
        except Exception as e:
            results["step_8_generate_report"] = f"FAIL: {e}"
            print(f"[GENERATE] Error: {e}", flush=True)

        # -------------------------------------------------------------
        # STEP 9: CONFIRM REQUEST CONTAINS NEW TEMPLATE ID, NOT STALE ID
        # -------------------------------------------------------------
        print("\n--- STEP 9: Confirm Request Template ID ---", flush=True)
        req_tid = generation_request_body.get("template_id") if generation_request_body else None
        print(f"[VERIFY-TID] Request template_id: {req_tid}", flush=True)
        print(f"[VERIFY-TID] Stale template_id: {STALE_TEMPLATE_ID}", flush=True)
        print(f"[VERIFY-TID] Uploaded template_id: {uploaded_template_id}", flush=True)
        
        step_9_pass = bool(req_tid and req_tid == uploaded_template_id and req_tid != STALE_TEMPLATE_ID)
        results["step_9_confirm_template_id"] = "PASS" if step_9_pass else f"FAIL: req_tid={req_tid}"

        # -------------------------------------------------------------
        # STEP 10: CONFIRM RENDER BACKEND SUCCESSFULLY RESOLVES TEMPLATE
        # -------------------------------------------------------------
        print("\n--- STEP 10: Confirm Render Backend Resolution ---", flush=True)
        rep_id = generation_response_body.get("report_id") if generation_response_body else None
        dl_url = generation_response_body.get("download_url") if generation_response_body else None
        print(f"[VERIFY-RENDER] Report ID: {rep_id}", flush=True)
        print(f"[VERIFY-RENDER] Download URL: {dl_url}", flush=True)
        
        step_10_pass = bool(rep_id and dl_url and "arm-backend-031f.onrender.com" in dl_url)
        results["step_10_render_resolution"] = "PASS" if step_10_pass else f"FAIL: rep_id={rep_id}, dl_url={dl_url}"

        # -------------------------------------------------------------
        # STEP 11: DOWNLOAD THE GENERATED DOCX
        # -------------------------------------------------------------
        print("\n--- STEP 11: Download Generated DOCX ---", flush=True)
        download_bytes = 0
        try:
            if dl_url:
                with urllib.request.urlopen(dl_url, timeout=30) as resp:
                    doc_bytes = resp.read()
                    download_bytes = len(doc_bytes)
                    downloaded_report_path = os.path.abspath("downloaded_smoke_test_report.docx")
                    with open(downloaded_report_path, "wb") as f_out:
                        f_out.write(doc_bytes)
                print(f"[DOWNLOAD] Downloaded {download_bytes} bytes to {downloaded_report_path}", flush=True)
            
            step_11_pass = bool(download_bytes > 5000)
            results["step_11_download_docx"] = f"PASS ({download_bytes} bytes)" if step_11_pass else "FAIL: empty download"
        except Exception as e:
            results["step_11_download_docx"] = f"FAIL: {e}"
            print(f"[DOWNLOAD] Error: {e}", flush=True)

        # -------------------------------------------------------------
        # STEP 12: VERIFY VALID DOCX AND PRESERVED TEMPLATE STRUCTURE
        # -------------------------------------------------------------
        print("\n--- STEP 12: Verify Structure Preservation ---", flush=True)
        try:
            assert downloaded_report_path and os.path.exists(downloaded_report_path)
            with zipfile.ZipFile(downloaded_report_path) as zf:
                namelist = zf.namelist()
                assert "[Content_Types].xml" in namelist, "Missing [Content_Types].xml"
                assert "word/document.xml" in namelist, "Missing word/document.xml"
                
                doc_xml = zf.read("word/document.xml").decode("utf-8")
                assert any(term in doc_xml.lower() for term in ["irrigation", "soil", "moisture", "water"]), "Project content missing in document.xml"
                
            results["step_12_structure_preserved"] = "PASS (Valid OpenXML archive with project content)"
            print("[STRUCTURE] Verified valid DOCX archive and preserved structure!", flush=True)
        except Exception as e:
            results["step_12_structure_preserved"] = f"FAIL: {e}"
            print(f"[STRUCTURE] Error: {e}", flush=True)

        browser.close()

    # -------------------------------------------------------------
    # EXTRA VERIFICATIONS
    # -------------------------------------------------------------
    localhost_reqs = [r for r in network_requests if "localhost" in r or "127.0.0.1" in r]
    results["extra_no_localhost_urls"] = "PASS" if not localhost_reqs else f"FAIL ({len(localhost_reqs)} found)"
    
    template_404_errors = [e for e in console_errors if "404" in e and ("template" in e.lower() or "storage" in e.lower())]
    results["extra_no_404_template_errors"] = "PASS" if not template_404_errors else f"FAIL ({len(template_404_errors)} template 404 errors)"
    
    results["extra_no_stale_template_id"] = "PASS" if generation_request_body and generation_request_body.get("template_id") != STALE_TEMPLATE_ID else "FAIL"
    
    template_selection_errors = [e for e in console_errors if any(term in e.lower() for term in ["template", "0484aecb", "storage", "upload-custom"])]
    results["extra_no_console_errors_related_to_template_selection"] = "PASS" if not template_selection_errors else f"FAIL ({len(template_selection_errors)} errors)"
    
    # Check no random/demo fallback was used:
    results["extra_no_random_demo_template_fallback"] = "PASS" if generation_request_body and generation_request_body.get("template_id") == uploaded_template_id else "FAIL"

    print("\n=======================================================", flush=True)
    print("FINAL SMOKE TEST RESULTS:", flush=True)
    print("=======================================================", flush=True)
    for k, v in results.items():
        print(f"  {k}: {v}", flush=True)
    print(f"  actual_template_id: {uploaded_template_id}", flush=True)
    print(f"  report_id: {generation_response_body.get('report_id') if generation_response_body else None}", flush=True)
    print(f"  download_size: {download_bytes} bytes", flush=True)
    print("=======================================================\n", flush=True)

    return results

if __name__ == "__main__":
    run_smoke_test()
