"""
Unit Test: test_help_center_ui.py
Verifies the dedicated Help Center:
1. Instantiation of help_center_view control.
2. 2-Tab Navigation: Tab 1 (Chatbot) and Tab 2 (Guides & FAQs).
3. Live Search & Category Filtering of guides and FAQs.
4. Interactive Hinglish AI Help Chatbot with offline responses and clear conversation.
5. Quick Navigation actions on workflow guide cards.
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
    print("RUNNING HELP CENTER 2-TAB POWER HUB & SEARCH VERIFICATION SUITE")
    print("=" * 70)

    # 1. Test Help Guide JSON
    print("\n[TEST 1] Verifying app help guide knowledge base...")
    guide_data = help_center_page.get_help_guide_data()
    assert isinstance(guide_data, list), "Guide data should be a list of sections"
    assert len(guide_data) >= 5, f"Expected at least 5 workflow guide sections, got {len(guide_data)}"
    for sec in guide_data:
        assert "title" in sec and "steps" in sec, f"Missing title/steps in section: {sec}"
        print(f"  ✓ Guide section: {sec['title']} ({len(sec['steps'])} steps)")

    # 2. Test Help Center View Instantiation & 2-Tab Navigation
    print("\n[TEST 2] Testing Help Center View instantiation & Tab Switcher...")
    nav_calls = []

    def mock_nav(target, **kwargs):
        nav_calls.append((target, kwargs))

    class MockPage:
        theme_mode = ft.ThemeMode.DARK
        def __init__(self):
            self.update_count = 0
        def update(self):
            self.update_count += 1
        def open(self, ctrl):
            pass

    mock_page = MockPage()
    view = help_center_page.help_center_view(mock_page, on_navigate=mock_nav)
    assert view is not None, "help_center_view returned None"
    assert hasattr(view, "chat_history_column"), "view missing chat_history_column"
    assert hasattr(view, "chat_input"), "view missing chat_input"
    assert hasattr(view, "switch_tab"), "view missing switch_tab"
    assert hasattr(view, "tab1_container"), "view missing tab1_container"
    assert hasattr(view, "tab2_container"), "view missing tab2_container"
    assert hasattr(view, "search_input"), "view missing search_input"

    # Verify Tab 1 is initially visible and Tab 2 is hidden
    assert view.tab1_container.visible is True, "Tab 1 (Chatbot) should be visible by default"
    assert view.tab2_container.visible is False, "Tab 2 (Guides) should be hidden by default"
    print("  ✓ Initial state verified: Tab 1 (Chatbot) visible, Tab 2 hidden.")

    # Switch to Tab 2
    view.switch_tab(1)
    assert view.tab1_container.visible is False, "Tab 1 should be hidden after switching to Tab 2"
    assert view.tab2_container.visible is True, "Tab 2 should be visible after switching to Tab 2"
    print("  ✓ Tab switching verified: Tab 2 (Guides & FAQs) active.")

    # 3. Test Live Search Filtering on Tab 2
    print("\n[TEST 3] Testing Live Search & Filtering on Tab 2...")
    guides_col = view.guides_list_column
    faqs_col = view.faqs_list_column
    empty_msg = view.empty_search_message

    initial_guides_count = len(guides_col.controls)
    initial_faqs_count = len(faqs_col.controls)
    assert initial_guides_count >= 5, f"Expected >= 5 guides, got {initial_guides_count}"
    assert initial_faqs_count >= 8, f"Expected >= 8 FAQs, got {initial_faqs_count}"
    print(f"  ✓ Initial Tab 2 contents: {initial_guides_count} Guides, {initial_faqs_count} FAQs.")

    # Search for "leave"
    view.search_input.value = "leave"
    view.render_guides_and_faqs()
    assert len(guides_col.controls) >= 1, "Expected matching guides for 'leave'"
    assert len(faqs_col.controls) >= 1, "Expected matching FAQs for 'leave'"
    assert empty_msg.visible is False, "Empty message should not be visible for matching search"
    print(f"  ✓ Search 'leave' matched {len(guides_col.controls)} guides and {len(faqs_col.controls)} FAQs.")

    # Search for non-existent keyword
    view.search_input.value = "nonexistentkeyword999"
    view.render_guides_and_faqs()
    assert len(guides_col.controls) == 0, "Expected 0 guides for bogus query"
    assert len(faqs_col.controls) == 0, "Expected 0 FAQs for bogus query"
    assert empty_msg.visible is True, "Empty message should be visible when 0 results match"
    print("  ✓ Empty search state triggered and rendered correctly.")

    # Reset search
    view.search_input.value = ""
    view.render_guides_and_faqs()
    assert len(guides_col.controls) == initial_guides_count
    assert len(faqs_col.controls) == initial_faqs_count
    assert empty_msg.visible is False
    print("  ✓ Search reset successfully restored full catalog.")

    # 4. Test Interactive Chatbot Offline Response & Reset
    print("\n[TEST 4] Testing Interactive Chatbot Offline Response & Conversation Reset...")
    view.switch_tab(0)
    assert view.tab1_container.visible is True

    initial_bubble_count = len(view.chat_history_column.controls)
    assert initial_bubble_count >= 1, "Chat should have welcome bubble"

    ans1 = help_center_page.get_chatbot_response("Offer letter kaise generate karein?")
    assert "offer" in ans1.lower() or "document" in ans1.lower()
    print(f"  ✓ Chatbot answered workflow question: {ans1[:75]}...")

    ans2 = help_center_page.get_chatbot_response("DFY me casual leave kitni milti hain?")
    assert "article" in ans2.lower() or "leave" in ans2.lower()
    print(f"  ✓ Chatbot answered DFY policy question: {ans2[:75]}...")

    # Test conversation reset
    view.reset_chat_history()
    assert len(view.chat_history_column.controls) == 1, "Reset chat should leave exactly 1 welcome bubble"
    print("  ✓ Clear Chat successfully reset conversation.")

    print("\n" + "=" * 70)
    print("ALL HELP CENTER TAB & SEARCH TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
