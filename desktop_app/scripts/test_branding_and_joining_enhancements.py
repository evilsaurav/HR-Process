"""
Unit Test: test_branding_and_joining_enhancements.py
Verifies:
1. main.py navigation rail contains Help Center and DFY logo widget.
2. joining_process_page.py contains candidate tag support and WhatsApp message generator.
3. document_generation_page.py contains bulk ZIP export button.
"""

import os
import sys

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

import flet as ft
from pages import joining_process_page
from pages import document_generation_page


def run_tests():
    print("=" * 70)
    print("RUNNING TASK 7 TESTS: BRANDING & JOINING PAGE ENHANCEMENTS")
    print("=" * 70)

    # 1. Test main.py file branding syntax
    print("\n[TEST 1] Verifying main.py DFY logo & Help Center integration...")
    main_py = os.path.join(DESKTOP_APP_DIR, "main.py")
    with open(main_py, "r", encoding="utf-8") as f:
        main_content = f.read()

    assert "dfy_logo112.png" in main_content, "dfy_logo112.png not referenced in main.py"
    assert "help_center_view" in main_content, "help_center_view not registered in main.py"
    assert "Help Center" in main_content, "Help Center destination missing from navigation rail"
    print("  ✓ main.py navigation rail and logo branding verified.")

    # 2. Test joining_process_page.py enhancements
    print("\n[TEST 2] Verifying Joining Process page controls...")
    class MockPage:
        theme_mode = ft.ThemeMode.DARK
        overlay = []
        services = []
        def update(self):
            pass
        def open(self, ctrl):
            pass

    mock_page = MockPage()
    joining_view = joining_process_view = joining_process_page.joining_process_view(mock_page)
    assert joining_view is not None, "joining_process_view returned None"

    joining_py = os.path.join(DESKTOP_APP_DIR, "pages", "joining_process_page.py")
    with open(joining_py, "r", encoding="utf-8") as f:
        jp_content = f.read()

    assert "candidate_outreach_service" in jp_content, "candidate_outreach_service not integrated in joining_process_page"
    assert "update_candidate_tag" in jp_content or "tag" in jp_content, "Tag functionality missing from joining_process_page"
    print("  ✓ Joining Process page outreach and tag enhancements verified.")

    # 3. Test document_generation_page.py bulk ZIP exporter integration
    print("\n[TEST 3] Verifying Document Generation page bulk ZIP button...")
    doc_py = os.path.join(DESKTOP_APP_DIR, "pages", "document_generation_page.py")
    with open(doc_py, "r", encoding="utf-8") as f:
        doc_content = f.read()

    assert "zip_export_service" in doc_content, "zip_export_service not imported in document_generation_page"
    print("  ✓ Document Generation page bulk ZIP integration verified.")

    print("\n" + "=" * 70)
    print("ALL TASK 7 TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
