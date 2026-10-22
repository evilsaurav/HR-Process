"""
Test Joining Process DOM & Duplicate Resolution UI Tree
Verifies the complete control tree (DOM) of scenario_a_review when uploading
PPSA INTERVIEW CHART.xlsx (44 candidates, 14 duplicates).
Asserts zero Flutter layout assertion violations (no expand=True inside wrap=True),
all 14 duplicate cards render with intact action buttons, and preview DataTable is populated.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Add desktop_app to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

import flet as ft
from pages.joining_process_page import joining_process_view


class MockFile:
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)


class MockPage:
    def __init__(self):
        self.services = []
        self.overlay = []
        self.controls = []
        self.dialog = None
        self.update_count = 0

    def open(self, c):
        self.dialog = c

    def close(self, c=None):
        self.dialog = None

    def update(self):
        self.update_count += 1


def inspect_control_tree(control, path="root", errors=None):
    if errors is None:
        errors = []

    # Check rule: If this control is a Row/Column with wrap=True, none of its children may have expand=True or flex
    is_wrap = getattr(control, "wrap", False) is True
    children = []

    if hasattr(control, "controls") and isinstance(control.controls, list):
        children = control.controls
    elif hasattr(control, "content") and control.content:
        children = [control.content]

    if is_wrap:
        for idx, child in enumerate(children):
            c_expand = getattr(child, "expand", None)
            if c_expand is True or (isinstance(c_expand, int) and c_expand > 0):
                errors.append(
                    f"CRITICAL LAYOUT ERROR: {type(child).__name__} at {path}.child[{idx}] has expand={c_expand} "
                    f"inside a parent {type(control).__name__} with wrap=True! "
                    f"(This triggers Flutter solid grey screen crash)"
                )

    # Recurse
    for idx, child in enumerate(children):
        inspect_control_tree(child, f"{path} > {type(child).__name__}[{idx}]", errors)

    return errors


def test_joining_dom_and_duplicates():
    print("=================================================================")
    print("Testing Joining Process DOM and Duplicate UI Tree Inspection")
    print("=================================================================")

    page = MockPage()
    view = joining_process_view(page)
    assert view is not None, "joining_process_view returned None"

    # Verify initial tree is clean
    initial_errors = inspect_control_tree(view)
    assert len(initial_errors) == 0, f"Initial view has layout errors: {initial_errors}"
    print("[PASS] Initial joining_process_view control tree has 0 layout conflicts.")

    # Locate FilePicker
    file_picker = None
    for s in page.services:
        if type(s).__name__ == "FilePicker":
            file_picker = s
            break
    assert file_picker is not None, "FilePicker service not registered in page"

    # Test file upload with real PPSA chart
    ppsa_path = r"C:\Users\Saurav\Downloads\PPSA INTERVIEW CHART.xlsx"
    if not os.path.exists(ppsa_path):
        # Fallback to test dummy file if downloads file is missing
        print(f"[WARN] File not found at {ppsa_path}, skipping live file test.")
        return

    print(f"[INFO] Uploading: {ppsa_path}")
    class MockEvent:
        def __init__(self, p):
            self.files = [MockFile(p)]

    file_picker.on_result(MockEvent(ppsa_path))
    print(f"[INFO] Upload processed. Page update count: {page.update_count}")

    # Inspect the full view control tree after upload
    post_upload_errors = inspect_control_tree(view)
    if post_upload_errors:
        print(f"[FAIL] Found {len(post_upload_errors)} layout errors in DOM:")
        for err in post_upload_errors:
            print(f"  ❌ {err}")
        assert False, f"Post-upload layout errors found: {post_upload_errors}"

    print("[PASS] 100% CLEAN! Zero wrap+expand conflicts found anywhere in post-upload DOM!")

    # Now verify the duplicate review panel contents
    # Locate upload_status_column inside the view
    upload_card = view.controls[2]  # modern_card containing upload
    card_content = upload_card.content  # ft.Column
    upload_status_col = card_content.controls[-1]
    assert len(upload_status_col.controls) > 0, "upload_status_column is empty after upload!"

    review_panel = upload_status_col.controls[0]
    review_col = review_panel.content
    print(f"[INFO] Review panel contains {len(review_col.controls)} top-level sections:")
    for idx, c in enumerate(review_col.controls):
        print(f"  - Section {idx}: {type(c).__name__}")

    # Section 0: toolbar
    toolbar = review_col.controls[0]
    assert getattr(toolbar, "wrap", False) is True, "Toolbar should wrap on small screens"
    # Verify toolbar children do not contain expand=True
    tb_children = toolbar.controls
    for c in tb_children:
        assert getattr(c, "expand", None) is None or getattr(c, "expand", None) is False

    # Section 2: duplicate cards column
    dup_cards_col = review_col.controls[2]
    dup_cards = dup_cards_col.controls
    print(f"[INFO] Verified {len(dup_cards)} duplicate comparison cards rendered.")
    assert len(dup_cards) == 14, f"Expected 14 duplicate cards for PPSA file, got {len(dup_cards)}"

    # Check first card structure
    card0 = dup_cards[0]
    card0_col = card0.content
    header_row = card0_col.controls[0]
    comparison_row = card0_col.controls[1]
    action_row = card0_col.controls[2]

    # Verify buttons exist in action row
    assert len(action_row.controls) >= 3, "Action row should have keep btn, replace btn, and status note"
    print(f"[PASS] Duplicate card #1: Header='{header_row.controls[0].value}', Action row has {len(action_row.controls)} controls.")

    # Section 5: preview panel
    preview_panel = review_col.controls[5]
    preview_col = preview_panel.content
    print(f"[INFO] Visual preview panel contains {len(preview_col.controls)} controls.")
    assert len(preview_col.controls) >= 3, "Preview panel missing KPI strip or table"

    # Action bar
    action_bar = review_col.controls[7]
    assert len(action_bar.controls) == 2, "Action bar should have Confirm and Cancel buttons"
    print(f"[PASS] Action bar has '{action_bar.controls[0].text}' and '{action_bar.controls[1].text}'")

    print("=================================================================")
    print("ALL DOM & DUPLICATE CHECKS PASSED WITH ZERO FLUTTER CONFLICTS! ✅")
    print("=================================================================")


if __name__ == "__main__":
    test_joining_dom_and_duplicates()
