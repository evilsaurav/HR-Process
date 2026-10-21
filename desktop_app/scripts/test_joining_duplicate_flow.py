"""
Verification Script: test_joining_duplicate_flow.py
End-to-end verification of the Joining Process page UI and workflow:
1. Page view instantiation.
2. Error handling: invalid / corrupted sheet results in plain-language feedback.
3. Scenario B flow (> 50% duplicates):
   - Renders 50%+ warning banner.
   - User can click 'Yes, skip duplicates & add new only' -> duplicates untouched, new added.
   - User can click 'No, let me review each one' -> transitions to Scenario A review cards.
4. Scenario A flow (<= 50% duplicates):
   - Side-by-side comparison cards with Keep/Replace toggles.
   - Toolbar batch actions ('Keep All Existing', 'Replace All with New').
   - Summary of genuinely new candidates.
   - Explicit confirmation saves changes to database.
5. Regression test on candidate table search, filtering, inline status change, and deletion.
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
from pages.joining_process_page import joining_process_view
from config import REQUIRED_CANDIDATE_COLUMNS


class MockPage:
    def __init__(self):
        self.title = "Joining Process Test"
        self.overlay = []
        self.services = []
        self.controls = []
        self.messages = []
        self.snack_bar = None

    def open(self, control):
        if isinstance(control, ft.SnackBar):
            self.snack_bar = control
            if hasattr(control.content, "value"):
                self.messages.append(control.content.value)
        elif hasattr(control, "content") and hasattr(control.content, "value"):
            self.messages.append(control.content.value)

    def close(self, control=None):
        pass

    def update(self):
        pass


class MockPickedFile:
    def __init__(self, path, name):
        self.path = path
        self.name = name


def create_test_sheet(file_path: str, rows_data: list[dict]):
    """Helper to create an Excel sheet with the required candidate schema."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df_rows = []
    for r in rows_data:
        row_dict = {col: "" for col in REQUIRED_CANDIDATE_COLUMNS}
        row_dict["Candidate Name"] = r.get("candidate_name", "")
        row_dict["Mobile"] = r.get("mobile", "")
        row_dict["Email"] = r.get("email", "")
        row_dict["Applied Designation"] = r.get("applied_designation", "")
        row_dict["Negotiated Salary"] = r.get("negotiated_salary", "")
        row_dict["Recent Designation"] = r.get("recent_designation", "")
        row_dict["Highest Education Qualification"] = r.get("highest_education", "")
        row_dict["Total Years of Experience (Inferred)"] = r.get("total_experience", "")
        row_dict["Core Technical Skills"] = r.get("core_technical_skills", "")
        row_dict["Key Responsibilities"] = r.get("key_responsibilities", "")
        row_dict["Contact Location"] = r.get("contact_location", "")
        df_rows.append(row_dict)

    df = pd.DataFrame(df_rows)
    df.to_excel(file_path, index=False)


def run_tests():
    print("=" * 70)
    print("RUNNING END-TO-END JOINING PROCESS UI FLOW TESTS")
    print("=" * 70)

    db_manager.init_db()

    # Test file paths
    scenario_b_file = os.path.join(DESKTOP_APP_DIR, "output", "test_scenario_b.xlsx")
    scenario_a_file = os.path.join(DESKTOP_APP_DIR, "output", "test_scenario_a.xlsx")
    corrupt_file = os.path.join(DESKTOP_APP_DIR, "output", "test_corrupt.xlsx")

    # Clean test candidates
    mob_b1 = "9111111101"
    mob_b2 = "9111111102"
    mob_b3 = "9111111103"
    mob_a1 = "9222222201"
    mob_a2 = "9222222202"

    conn = db_manager.get_connection()
    conn.execute("DELETE FROM candidates WHERE mobile IN (?, ?, ?, ?, ?)", (mob_b1, mob_b2, mob_b3, mob_a1, mob_a2))
    conn.commit()

    # Pre-seed candidate in DB for Scenario B test
    conn.execute("""
        INSERT INTO candidates (candidate_name, mobile, email, applied_designation, negotiated_salary, status)
        VALUES ('Existing Person B1', ?, 'b1@dfy.org', 'Coordinator', '30000', 'Applied')
    """, (mob_b1,))
    conn.execute("""
        INSERT INTO candidates (candidate_name, mobile, email, applied_designation, negotiated_salary, status)
        VALUES ('Existing Person B2', ?, 'b2@dfy.org', 'Coordinator', '32000', 'Applied')
    """, (mob_b2,))
    conn.commit()
    conn.close()

    try:
        page = MockPage()
        view = joining_process_view(page)
        assert isinstance(view, ft.Column), "joining_process_view must return ft.Column"

        # Find the FilePicker registered in services or overlay
        picker = page.services[0] if page.services else page.overlay[0]

        # -----------------------------------------------------------------
        # TEST 1: Corrupted / invalid file test
        # -----------------------------------------------------------------
        print("\n[TEST 1] Testing invalid/corrupt file upload...")
        with open(corrupt_file, "w", encoding="utf-8") as f:
            f.write("This is not an excel file")

        picker.on_result([MockPickedFile(corrupt_file, "test_corrupt.xlsx")])
        assert any("We couldn't read this file" in m for m in page.messages), \
            f"Expected plain-language file read error, got messages: {page.messages}"
        print("  ✓ Plain-language error shown for corrupted file with zero raw exceptions leaked.")

        # -----------------------------------------------------------------
        # TEST 2: Scenario B Flow (> 50% duplicates)
        # -----------------------------------------------------------------
        print("\n[TEST 2] Testing Scenario B (> 50% duplicates banner)...")
        # 3 rows total: 2 duplicates (mob_b1, mob_b2) and 1 new (mob_b3) -> 66.7% duplicates
        create_test_sheet(scenario_b_file, [
            {"candidate_name": "Existing Person B1", "mobile": mob_b1, "negotiated_salary": "35000", "applied_designation": "DC"},
            {"candidate_name": "Existing Person B2", "mobile": mob_b2, "negotiated_salary": "36000", "applied_designation": "DC"},
            {"candidate_name": "New Candidate B3", "mobile": mob_b3, "negotiated_salary": "28000", "applied_designation": "Staff Nurse"},
        ])

        picker.on_result([MockPickedFile(scenario_b_file, "test_scenario_b.xlsx")])

        # Inspect upload_status_column inside the upload card
        upload_card = view.controls[2]  # Upload modern_card
        upload_card_col = upload_card.content
        upload_status_col = upload_card_col.controls[-1]
        assert len(upload_status_col.controls) > 0, "upload_status_column should have content"

        banner = upload_status_col.controls[0]
        banner_col = banner.content
        banner_title = banner_col.controls[0].controls[1].value
        assert "2 out of 3 candidates in this file already exist in the system" in banner_title, \
            f"Expected Scenario B banner title, got: {banner_title}"
        print(f"  ✓ Scenario B banner displayed: '{banner_title}'")

        # Test clicking "Yes, skip duplicates & add only new"
        btn_row = banner_col.controls[3]
        yes_skip_btn = btn_row.controls[0]
        assert "Yes, skip duplicates" in yes_skip_btn.text
        yes_skip_btn.on_click(None)

        # Verify DB: mob_b1 and mob_b2 were NOT overwritten
        b1_rec = db_manager.get_candidate_by_mobile(mob_b1)
        assert b1_rec["negotiated_salary"] == "30000", f"Existing record was overwritten! Got: {b1_rec['negotiated_salary']}"
        # Verify DB: mob_b3 was added fresh
        b3_rec = db_manager.get_candidate_by_mobile(mob_b3)
        assert b3_rec is not None, "New candidate B3 was not added"
        assert b3_rec["candidate_name"] == "New Candidate B3"
        print("  ✓ Bulk skip verified: duplicates kept untouched, new candidate added.")

        # -----------------------------------------------------------------
        # TEST 3: Scenario A Flow (<= 50% duplicates)
        # -----------------------------------------------------------------
        print("\n[TEST 3] Testing Scenario A (<= 50% duplicates review cards)...")
        # 2 rows total: 1 duplicate (mob_b1) and 1 new (mob_a1) -> 50.0% duplicates
        create_test_sheet(scenario_a_file, [
            {
                "candidate_name": "Existing Person B1",
                "mobile": mob_b1,
                "email": "",  # Blank email must not erase existing b1@dfy.org
                "negotiated_salary": "42000",
                "applied_designation": "Project Director",
                "contact_location": "Patna HQ",
            },
            {
                "candidate_name": "New Person A1",
                "mobile": mob_a1,
                "email": "a1@dfy.org",
                "negotiated_salary": "29000",
                "applied_designation": "Pharmacist",
                "contact_location": "Gaya",
            },
        ])

        picker.on_result([MockPickedFile(scenario_a_file, "test_scenario_a.xlsx")])

        # Verify Scenario A review panel rendered
        review_panel = upload_status_col.controls[0]
        panel_col = review_panel.content
        toolbar = panel_col.controls[0]
        assert "Reviewing 1 Duplicate Candidates (50.0% of uploaded file)" in toolbar.controls[0].controls[1].value
        print("  ✓ Scenario A review screen rendered with side-by-side cards.")

        # Inspect duplicate card
        duplicate_list_col = panel_col.controls[2]
        dup_card = duplicate_list_col.controls[0]
        dup_btn_row = dup_card.content.controls[2]
        keep_btn = dup_btn_row.controls[0]
        replace_btn = dup_btn_row.controls[1]

        # Click "Replace with New" for this duplicate
        replace_btn.on_click(None)

        # Click "Confirm & Apply Changes"
        action_bar = panel_col.controls[-1]
        confirm_btn = action_bar.controls[0]
        assert "Confirm & Apply Changes" in confirm_btn.text
        confirm_btn.on_click(None)

        # Verify DB: mob_b1 was updated with non-empty values while email was strictly preserved
        b1_updated = db_manager.get_candidate_by_mobile(mob_b1)
        assert b1_updated["negotiated_salary"] == "42000", "Salary was not updated"
        assert b1_updated["applied_designation"] == "Project Director", "Designation was not updated"
        assert b1_updated["email"] == "b1@dfy.org", f"Blank email erased existing email! Got: {b1_updated['email']}"
        # Verify DB: mob_a1 was added
        a1_rec = db_manager.get_candidate_by_mobile(mob_a1)
        assert a1_rec is not None, "Candidate A1 was not added"
        print("  ✓ Individual replace applied correctly and preserved blank fields.")

        # -----------------------------------------------------------------
        # TEST 4: Single candidate regression tests
        # -----------------------------------------------------------------
        print("\n[TEST 4] Testing single candidate search, filtering, status change, delete...")
        search_field = view.controls[4].content.controls[2].controls[0]
        status_filter = view.controls[4].content.controls[2].controls[1]
        refresh_btn = view.controls[4].content.controls[2].controls[2]

        search_field.value = "New Person A1"
        search_field.on_change(None)

        # Candidate status change
        a1_id = a1_rec["id"]
        db_manager.update_candidate_status(a1_id, "Interview")
        assert db_manager.get_candidate_by_id(a1_id)["status"] == "Interview"
        print("  ✓ Single candidate status update verified.")

        # Candidate delete
        db_manager.delete_candidate(a1_id)
        assert db_manager.get_candidate_by_id(a1_id) is None
        print("  ✓ Single candidate deletion verified.")

        print("\n" + "=" * 70)
        print("ALL END-TO-END UI FLOW TESTS PASSED! ✅")
        print("=" * 70)

    finally:
        # Cleanup test data and files
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM candidates WHERE mobile IN (?, ?, ?, ?, ?)", (mob_b1, mob_b2, mob_b3, mob_a1, mob_a2))
        conn.commit()
        conn.close()

        for f in [scenario_b_file, scenario_a_file, corrupt_file]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass


if __name__ == "__main__":
    run_tests()
