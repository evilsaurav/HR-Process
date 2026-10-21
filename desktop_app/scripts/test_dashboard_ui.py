"""
Verification Script: test_dashboard_ui.py
Tests the Dashboard UI Page (Part 4):
1. Instantiating dashboard_view without errors.
2. Verifying stat cards render with numeric counts.
3. Verifying experience certificates due section renders.
4. Verifying increment reminders section renders.
5. Verifying Keka sync status section renders.
6. Triggering Excel export button on the dashboard and verifying file generation.
"""

import os
import sys
import pandas as pd

# Configure UTF-8 encoding for Windows console output
sys.stdout.reconfigure(encoding="utf-8")

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

import flet as ft
from database import db_manager
from pages.dashboard_page import dashboard_view


class MockPage:
    def __init__(self):
        self.title = "Test"
        self.overlay = []
        self.controls = []
        self.messages = []

    def open(self, control):
        if hasattr(control, "content") and hasattr(control.content, "value"):
            self.messages.append(control.content.value)
        elif hasattr(control, "text"):
            self.messages.append(control.text)

    def close(self, control=None):
        pass

    def update(self):
        pass


def run_dashboard_ui_tests():
    print("=" * 70)
    print("PART 4 VERIFICATION: DASHBOARD UI PAGE")
    print("=" * 70)

    db_manager.init_db()

    page = MockPage()
    view = dashboard_view(page)
    print("1. Dashboard view instantiated successfully.")

    # Layout structure:
    # controls[0]: Header
    # controls[1]: Spacing
    # controls[2]: Stat Cards Row
    # controls[3]: Spacing
    # controls[4]: Experience Certificate Due Card
    # controls[5]: Spacing
    # controls[6]: Increment Reminders Card
    # controls[7]: Spacing
    # controls[8]: Keka Sync Status Card

    # 2. Verify Stat Cards
    stat_row = view.controls[2]
    stat_items = stat_row.controls
    print(f"\n2. Stat cards rendered count: {len(stat_items)}")
    assert len(stat_items) >= 7, "Must render stat cards for all pipeline statuses + total"

    stat_summary = {}
    for card_ctrl in stat_items:
        card_col = card_ctrl.content
        count_text = card_col.controls[1].value
        label_text = card_col.controls[2].value
        stat_summary[label_text] = count_text
        print(f"   • {label_text}: {count_text}")

    assert "Total" in stat_summary, "Total stat card missing"
    assert "Joined" in stat_summary, "Joined stat card missing"
    assert int(stat_summary["Total"]) >= 0
    print("   ✅ Stat cards verified.")

    # 3. Verify Experience Certificate Due Card
    exp_card = view.controls[4]
    exp_col = exp_card.content
    print(f"\n3. Experience certificates due section:")
    assert exp_col is not None
    exp_header_row = exp_col.controls[0]
    exp_export_btn = exp_header_row.controls[2]
    print(f"   Export button text: {exp_export_btn.text}")
    assert "Export to Excel" in (exp_export_btn.text or "")

    # 4. Verify Increment Reminders Card
    inc_card = view.controls[6]
    inc_col = inc_card.content
    print(f"\n4. Increment reminders section:")
    assert inc_col is not None
    inc_items_col = inc_col.controls[3]
    print(f"   Increment controls inside section: {len(inc_items_col.controls)}")
    assert len(inc_items_col.controls) > 0
    print("   ✅ Increment reminders section verified.")

    # 5. Verify Keka Sync Status Card
    keka_card = view.controls[8]
    keka_col = keka_card.content
    print(f"\n5. Keka sync status section:")
    assert keka_col is not None
    keka_tile = keka_col.controls[2]
    assert keka_tile is not None
    print("   ✅ Keka sync status section verified.")

    # 6. Test Excel Export Action
    print("\n6. Testing Excel export trigger from Dashboard...")
    exp_export_btn.on_click(None)
    expected_export_path = os.path.join(DESKTOP_APP_DIR, "output", "experience_certificates_due.xlsx")
    assert os.path.exists(expected_export_path), f"Export file {expected_export_path} was not created"
    df_exp = pd.read_excel(expected_export_path)
    print(f"   Exported Excel shape: {df_exp.shape}")
    print(f"   Exported Excel columns: {list(df_exp.columns)}")
    assert "Candidate Name" in df_exp.columns
    assert "Certificate Issued" in df_exp.columns
    print("   ✅ Excel export action verified.")

    print("\n" + "=" * 70)
    print("ALL PART 4 DASHBOARD UI TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_dashboard_ui_tests()
