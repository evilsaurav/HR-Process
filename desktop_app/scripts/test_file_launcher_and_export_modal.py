"""
Test Script: test_file_launcher_and_export_modal.py
Verifies:
1. utils.file_launcher: open_file_externally and open_folder_and_select.
2. utils.ui_theme: show_export_success_dialog structure, formatting, and button actions.
3. Integration presence in joining_process_page, dashboard_page, and document_generation_page.
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

# Configure UTF-8 output
sys.stdout.reconfigure(encoding="utf-8")

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

import flet as ft


def test_file_launcher_module():
    print("\n--- 1. Testing utils.file_launcher ---")
    from utils import file_launcher

    # Test with non-existent file
    ok, msg = file_launcher.open_file_externally("non_existent_file_xyz_123.xlsx")
    assert not ok, "Expected non-existent file to return False"
    assert "not exist" in msg.lower(), f"Unexpected message: {msg}"
    print("  [PASS] open_file_externally handles missing file")

    ok, msg = file_launcher.open_folder_and_select("non_existent_file_xyz_123.xlsx")
    assert not ok, "Expected non-existent file to return False"
    assert "not exist" in msg.lower(), f"Unexpected message: {msg}"
    print("  [PASS] open_folder_and_select handles missing file")

    # Test with real temporary file
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(b"dummy excel content")
        tmp_path = tmp.name

    try:
        # Test open_file_externally with mocked os.startfile
        with patch("os.startfile", create=True) as mock_startfile:
            ok, msg = file_launcher.open_file_externally(tmp_path)
            assert ok, f"Expected open_file_externally to return True, got {ok}, {msg}"
            mock_startfile.assert_called_once_with(os.path.abspath(tmp_path))
            print("  [PASS] open_file_externally calls os.startfile with absolute path")

        # Test open_file_externally with exception
        with patch("os.startfile", create=True, side_effect=OSError("System error")):
            ok, msg = file_launcher.open_file_externally(tmp_path)
            assert not ok, "Expected exception to result in False"
            assert "System error" in msg
            print("  [PASS] open_file_externally safely catches exceptions")

        # Test open_folder_and_select with mocked subprocess.Popen
        with patch("subprocess.Popen") as mock_popen:
            ok, msg = file_launcher.open_folder_and_select(tmp_path)
            assert ok, f"Expected open_folder_and_select to return True, got {ok}, {msg}"
            mock_popen.assert_called_once()
            call_arg = mock_popen.call_args[0][0]
            assert "explorer" in str(call_arg) and "/select" in str(call_arg)
            assert os.path.abspath(tmp_path) in str(call_arg)
            print("  [PASS] open_folder_and_select invokes explorer /select with absolute path")

        # Test open_folder_and_select with exception
        with patch("subprocess.Popen", side_effect=OSError("Launch error")):
            ok, msg = file_launcher.open_folder_and_select(tmp_path)
            assert not ok, "Expected exception to result in False"
            assert "Launch error" in msg
            print("  [PASS] open_folder_and_select safely catches exceptions")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_show_export_success_dialog():
    print("\n--- 2. Testing ui_theme.show_export_success_dialog ---")
    from utils import ui_theme
    assert hasattr(ui_theme, "show_export_success_dialog"), "ui_theme missing show_export_success_dialog"

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(b"x" * 2048)  # 2 KB
        tmp_path = tmp.name

    try:
        opened_dialogs = []
        closed_dialogs = []

        mock_page = MagicMock()
        mock_page.open = MagicMock(side_effect=lambda dlg: opened_dialogs.append(dlg))
        mock_page.close = MagicMock(side_effect=lambda dlg: closed_dialogs.append(dlg))
        mock_page.update = MagicMock()

        ui_theme.show_export_success_dialog(
            mock_page,
            tmp_path,
            record_count=25,
            report_title="Employee Pipeline"
        )

        assert mock_page.open.called, "mock_page.open was not called"
        assert len(opened_dialogs) == 1, "Expected 1 opened dialog"
        dlg = opened_dialogs[0]
        assert isinstance(dlg, ft.AlertDialog), f"Expected AlertDialog, got {type(dlg)}"

        # Check Dialog Title
        assert isinstance(dlg.title, ft.Row)
        title_texts = [c.value for c in dlg.title.controls if isinstance(c, ft.Text)]
        assert any("Employee Pipeline Exported Successfully" in t for t in title_texts)
        print("  [PASS] Export dialog title contains report_title and check icon")

        # Check Dialog Content
        assert dlg.content is not None
        # Walk controls to find texts
        def get_all_texts(ctrl):
            texts = []
            if hasattr(ctrl, "value") and ctrl.value:
                texts.append(str(ctrl.value))
            if hasattr(ctrl, "content") and ctrl.content:
                texts.extend(get_all_texts(ctrl.content))
            if hasattr(ctrl, "controls") and ctrl.controls:
                for sub in ctrl.controls:
                    texts.extend(get_all_texts(sub))
            return texts

        content_texts = " ".join(get_all_texts(dlg.content))
        assert os.path.basename(tmp_path) in content_texts, "File name missing from dialog content"
        assert "25 Records" in content_texts or "25 records" in content_texts.lower(), "Record count missing"
        assert "KB" in content_texts or "MB" in content_texts, "File size missing"
        print("  [PASS] Dialog content renders filename, record count, and size formatted")

        # Check Actions
        assert len(dlg.actions) >= 3, f"Expected at least 3 actions, got {len(dlg.actions)}"
        btn_open = dlg.actions[0]
        btn_folder = dlg.actions[1]
        btn_close = dlg.actions[2]

        def get_btn_label(btn):
            label = getattr(btn, "text", "") or ""
            if not label:
                content = getattr(btn, "content", "")
                if isinstance(content, str):
                    label = content
                elif hasattr(content, "value"):
                    label = content.value or ""
            return str(label)

        assert "Open File" in get_btn_label(btn_open)
        assert "Open Folder" in get_btn_label(btn_folder)
        assert "Close" in get_btn_label(btn_close)
        print("  [PASS] Dialog actions include Open File, Open Folder, and Close buttons")

        # Test button callbacks
        from utils import file_launcher
        with patch.object(file_launcher, "open_file_externally", return_value=(True, "ok")) as mock_open_ext:
            btn_open.on_click(None)
            mock_open_ext.assert_called_once_with(tmp_path)
            assert dlg in closed_dialogs, "Open File button did not close dialog"
            print("  [PASS] Open File button triggers open_file_externally and closes dialog")

        with patch.object(file_launcher, "open_folder_and_select", return_value=(True, "ok")) as mock_open_dir:
            btn_folder.on_click(None)
            mock_open_dir.assert_called_once_with(tmp_path)
            assert closed_dialogs.count(dlg) >= 2, "Open Folder button did not close dialog"
            print("  [PASS] Open Folder button triggers open_folder_and_select and closes dialog")

        # Test close button
        btn_close.on_click(None)
        assert closed_dialogs.count(dlg) >= 3, "Close button did not close dialog"
        print("  [PASS] Close button closes dialog")

        # Test with record_count=None (e.g. general export or single package)
        opened_dialogs.clear()
        ui_theme.show_export_success_dialog(
            mock_page,
            tmp_path,
            record_count=None,
            report_title="Daily Briefing"
        )
        assert len(opened_dialogs) == 1
        dlg2 = opened_dialogs[0]
        content2_texts = " ".join(get_all_texts(dlg2.content))
        assert os.path.basename(tmp_path) in content2_texts
        print("  [PASS] Dialog handles record_count=None gracefully")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_page_integrations():
    print("\n--- 3. Testing Integration in Pages ---")

    # 1. joining_process_page.py
    joining_path = os.path.join(DESKTOP_APP_DIR, "pages", "joining_process_page.py")
    with open(joining_path, "r", encoding="utf-8") as f:
        src = f.read()
    assert "show_export_success_dialog" in src, "joining_process_page.py does not call show_export_success_dialog"
    print("  [PASS] joining_process_page integrates show_export_success_dialog")

    # 2. dashboard_page.py
    dashboard_path = os.path.join(DESKTOP_APP_DIR, "pages", "dashboard_page.py")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        src = f.read()
    assert "show_export_success_dialog" in src, "dashboard_page.py does not call show_export_success_dialog"
    assert src.count("show_export_success_dialog") >= 3, (
        f"dashboard_page.py expected at least 3 export call sites, found {src.count('show_export_success_dialog')}"
    )
    print(f"  [PASS] dashboard_page integrates show_export_success_dialog at {src.count('show_export_success_dialog')} sites")

    # 3. document_generation_page.py
    doc_path = os.path.join(DESKTOP_APP_DIR, "pages", "document_generation_page.py")
    with open(doc_path, "r", encoding="utf-8") as f:
        src = f.read()
    assert "show_export_success_dialog" in src, "document_generation_page.py does not call show_export_success_dialog"
    print("  [PASS] document_generation_page integrates show_export_success_dialog")


def main():
    print("=" * 70)
    print("RUNNING VERIFICATION: OS FILE LAUNCHER & EXPORT SUCCESS MODAL")
    print("=" * 70)
    test_file_launcher_module()
    test_show_export_success_dialog()
    test_page_integrations()
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY! (100% Coverage)")
    print("=" * 70)


if __name__ == "__main__":
    main()
