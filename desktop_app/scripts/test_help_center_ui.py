"""
Unit Test: test_help_center_ui.py
Verifies the dedicated Help Center:
1. Instantiation of help_center_view control.
2. Rendering of step-by-step visual workflow guide cards.
3. Interactive Hinglish AI Help Chatbot answering user questions with offline fallback.
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
from pages import help_center_page


def run_tests():
    print("=" * 70)
    print("RUNNING TASK 5 TESTS: DEDICATED HELP CENTER & HINGLISH CHATBOT")
    print("=" * 70)

    # 1. Test Help Guide JSON
    print("\n[TEST 1] Verifying app help guide knowledge base...")
    guide_data = help_center_page.get_help_guide_data()
    assert isinstance(guide_data, list), "Guide data should be a list of sections"
    assert len(guide_data) >= 5, f"Expected at least 5 workflow guide sections, got {len(guide_data)}"
    for sec in guide_data:
        assert "title" in sec and "steps" in sec, f"Missing title/steps in section: {sec}"
        print(f"  ✓ Guide section: {sec['title']} ({len(sec['steps'])} steps)")

    # 2. Test Help Center View Instantiation
    print("\n[TEST 2] Testing Help Center View instantiation...")
    nav_calls = []

    def mock_nav(target, **kwargs):
        nav_calls.append((target, kwargs))

    # Mock Flet Page
    class MockPage:
        theme_mode = ft.ThemeMode.DARK
        def update(self):
            pass
        def open(self, ctrl):
            pass

    mock_page = MockPage()
    view = help_center_page.help_center_view(mock_page, on_navigate=mock_nav)
    assert view is not None, "help_center_view returned None"
    assert hasattr(view, "chat_history_column"), "view missing chat_history_column"
    assert hasattr(view, "chat_input"), "view missing chat_input"
    print("  ✓ Help Center UI controls instantiated successfully.")

    # 3. Test Interactive Chatbot Offline Response
    print("\n[TEST 3] Testing Interactive Chatbot Offline Response...")
    ans1 = help_center_page.get_chatbot_response("Offer letter kaise generate karein?")
    assert "offer" in ans1.lower() or "document" in ans1.lower()
    print(f"  ✓ Chatbot answered workflow question: {ans1[:90]}...")

    ans2 = help_center_page.get_chatbot_response("DFY me casual leave kitni milti hain?")
    assert "article" in ans2.lower() or "leave" in ans2.lower()
    print(f"  ✓ Chatbot answered DFY policy question: {ans2[:90]}...")

    ans3 = help_center_page.get_chatbot_response("Duplicate candidate aa jaye to kya karna hai?")
    assert "duplicate" in ans3.lower() or "sheet" in ans3.lower()
    print(f"  ✓ Chatbot answered duplicate question: {ans3[:90]}...")

    print("\n" + "=" * 70)
    print("ALL TASK 5 TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
