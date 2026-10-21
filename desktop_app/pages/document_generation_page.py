"""
Page: document_generation_page.py
Purpose: Flagship Smart Document Pipeline & Staging Hub for DFY HRMS Desktop.
Combines:
- Tab 1: 🔍 Smart Detection & Generator (scans Keka data, evaluates smart rules,
         supports HR override, batch generates to staging queue).
- Tab 2: 📋 Staging & Final Review Hub (Human-in-the-Loop review, OS file preview,
         instant inline fix & regeneration, format toggle, and atomic Final Go bulk dispatch).
- Tab 3: ✍️ Manual One-Off Generator (preserves one-off document generation,
         dynamic template overrides, and audit log history).
"""

import os
import subprocess
import traceback
import datetime
from typing import Optional, List, Dict, Any
import flet as ft

from config import PRIMARY_COLOR, DESKTOP_APP_DIR
from database import db_manager
from services import (
    document_generation_service,
    document_staging_service,
    smart_rule_detector,
    pdf_converter_service,
    excel_export_service,
    email_service,
)
from utils.email_preview_modal import open_email_preview_modal
from utils.ui_theme import (
    modern_card,
    page_header,
    section_title,
    status_badge,
    primary_button,
    secondary_button,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_CARD_BG_HOVER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_PRIMARY,
    COLOR_PRIMARY_LIGHT,
    COLOR_SECONDARY,
    COLOR_SECONDARY_LIGHT,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_ERROR,
    COLOR_INFO,
)

DOC_TYPE_OPTIONS = [
    ("Offer Letter", "offer"),
    ("Appointment Letter", "appointment"),
    ("Increment Letter", "increment"),
    ("Extension Letter", "extension"),
    ("Internship Letter", "internship"),
    ("Consultant Agreement", "consultant"),
    ("Experience Certificate", "experience"),
    ("Salary Certificate", "salary"),
    ("Termination Letter", "termination"),
]

OVERRIDE_DOC_TYPE_OPTIONS = [
    ("Offer Letter", "offer"),
    ("Appointment Letter", "appointment"),
    ("Extension Letter", "extension"),
    ("Increment Letter", "increment"),
    ("Experience Certificate", "experience_certificate"),
    ("Salary Certificate", "salary_certificate"),
    ("Termination Letter", "termination"),
    ("None (Skip)", "none"),
]


def open_file_safe(file_path: str) -> bool:
    """Safely opens a file or directory using the OS default application."""
    if not file_path or not os.path.exists(file_path):
        return False
    try:
        if hasattr(os, "startfile"):
            os.startfile(file_path)
            return True
        else:
            subprocess.Popen(["xdg-open", file_path])
            return True
    except Exception as ex:
        print(f"Error opening file {file_path}: {ex}")
        return False


def map_suggested_to_option(doc_type_raw: str) -> str:
    """Maps raw detector doc type strings to override options."""
    if not doc_type_raw:
        return "offer"
    dt = str(doc_type_raw).strip().lower()
    if "offer" in dt:
        return "offer"
    if "appointment" in dt:
        return "appointment"
    if "extension" in dt:
        return "extension"
    if "increment" in dt:
        return "increment"
    if "experience" in dt:
        return "experience_certificate"
    if "salary" in dt:
        return "salary_certificate"
    if "termination" in dt:
        return "termination"
    if dt in ["none", "skip"]:
        return "none"
    return "offer"


def get_doc_badge(doc_type: str) -> ft.Container:
    """Returns color-coded badge container for document types."""
    dt = str(doc_type or "").lower()
    if "offer" in dt or "appointment" in dt:
        lbl = "Appointment" if "appointment" in dt else "Offer Letter"
        return ft.Container(
            content=ft.Text(lbl, size=11, weight=ft.FontWeight.BOLD, color=COLOR_PRIMARY_LIGHT),
            bgcolor="#1E3A8A",
            border=ft.Border.all(1, "#2563EB"),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
        )
    elif "extension" in dt:
        return ft.Container(
            content=ft.Text("Extension", size=11, weight=ft.FontWeight.BOLD, color=COLOR_SECONDARY_LIGHT),
            bgcolor="#4C1D95",
            border=ft.Border.all(1, "#7C3AED"),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
        )
    elif "increment" in dt:
        return ft.Container(
            content=ft.Text("Increment", size=11, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS),
            bgcolor="#064E3B",
            border=ft.Border.all(1, "#059669"),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
        )
    elif "experience" in dt:
        return ft.Container(
            content=ft.Text("Experience Cert", size=11, weight=ft.FontWeight.BOLD, color=COLOR_WARNING),
            bgcolor="#78350F",
            border=ft.Border.all(1, "#D97706"),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
        )
    elif "salary" in dt:
        return ft.Container(
            content=ft.Text("Salary Cert", size=11, weight=ft.FontWeight.BOLD, color=COLOR_INFO),
            bgcolor="#164E63",
            border=ft.Border.all(1, "#0891B2"),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
        )
    elif "termination" in dt:
        return ft.Container(
            content=ft.Text("Termination", size=11, weight=ft.FontWeight.BOLD, color=COLOR_ERROR),
            bgcolor="#7F1D1D",
            border=ft.Border.all(1, "#DC2626"),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
        )
    else:
        return status_badge(doc_type.replace("_", " ").title())


def document_generation_view(page: ft.Page, initial_tab: int = 0):
    db_manager.init_db()

    # Centralized State
    state = {
        # Active view: 0=Detection, 1=Staging Hub, 2=Manual One-off
        "active_tab": 0,

        # Tab 1: Smart Detection
        "detected_needs": [],
        "selected_detected_ids": set(),
        "detection_overrides": {},
        "detection_search_filter": "",
        "detection_loading": False,

        # Tab 2: Staging & Review Hub
        "staged_records": [],
        "selected_staging_ids": set(),
        "staging_status_filter": "Staged",
        "staging_search_filter": "",
        "staging_loading": False,

        # Tab 3: Manual Generator
        "selected_candidate_id": None,
        "selected_candidate": None,
        "selected_doc_type": "offer",
        "manual_override_desig": None,
        "preview_generated": False,
        "last_preview_path": None,
        "last_final_path": None,
    }

    # Snackbar notification helper
    def show_message(text: str, is_success: bool = True):
        try:
            page.open(
                ft.SnackBar(
                    ft.Text(text),
                    bgcolor=ft.Colors.GREEN if is_success else ft.Colors.RED,
                )
            )
            page.update()
        except Exception:
            pass

    # =========================================================================
    # TAB SWITCHER CONTROLS
    # =========================================================================

    tab1_counter_text = ft.Text("0", size=11, weight=ft.FontWeight.BOLD, color=COLOR_PRIMARY_LIGHT)
    tab1_badge = ft.Container(
        content=tab1_counter_text,
        bgcolor="#1E3A8A",
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
        border_radius=10,
    )

    tab2_counter_text = ft.Text("0", size=11, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS)
    tab2_badge = ft.Container(
        content=tab2_counter_text,
        bgcolor="#064E3B",
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
        border_radius=10,
    )

    tab1_header_btn = ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        border_radius=10,
        bgcolor=COLOR_CARD_BG_HOVER,
        border=ft.Border.all(1, COLOR_PRIMARY_LIGHT),
        content=ft.Row([
            ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=COLOR_PRIMARY_LIGHT, size=18),
            ft.Text("Tab 1: Smart Detection & Generator", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
            tab1_badge,
        ], spacing=8, tight=True),
        on_click=lambda e: switch_tab(0),
    )

    tab2_header_btn = ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        border_radius=10,
        bgcolor=COLOR_CARD_BG,
        border=ft.Border.all(1, COLOR_CARD_BORDER),
        content=ft.Row([
            ft.Icon(ft.Icons.RULE_FOLDER_ROUNDED, color=COLOR_SUCCESS, size=18),
            ft.Text("Tab 2: Staging & Final Review Hub", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
            tab2_badge,
        ], spacing=8, tight=True),
        on_click=lambda e: switch_tab(1),
    )

    tab3_header_btn = ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        border_radius=10,
        bgcolor=COLOR_CARD_BG,
        border=ft.Border.all(1, COLOR_CARD_BORDER),
        content=ft.Row([
            ft.Icon(ft.Icons.EDIT_NOTE_ROUNDED, color=COLOR_TEXT_MUTED, size=18),
            ft.Text("Manual One-Off Generator", weight=ft.FontWeight.W_500, size=13, color=COLOR_TEXT_SECONDARY),
        ], spacing=8, tight=True),
        on_click=lambda e: switch_tab(2),
    )

    tab_switcher_row = ft.Row([
        tab1_header_btn,
        tab2_header_btn,
        tab3_header_btn,
    ], spacing=10)

    # View containers for tabs
    tab1_container = ft.Container()
    tab2_container = ft.Container()
    tab3_container = ft.Container()

    def update_tab_header_styles():
        curr = state["active_tab"]
        tab1_header_btn.bgcolor = COLOR_CARD_BG_HOVER if curr == 0 else COLOR_CARD_BG
        tab1_header_btn.border = ft.Border.all(1, COLOR_PRIMARY_LIGHT if curr == 0 else COLOR_CARD_BORDER)

        tab2_header_btn.bgcolor = COLOR_CARD_BG_HOVER if curr == 1 else COLOR_CARD_BG
        tab2_header_btn.border = ft.Border.all(1, COLOR_SUCCESS if curr == 1 else COLOR_CARD_BORDER)

        tab3_header_btn.bgcolor = COLOR_CARD_BG_HOVER if curr == 2 else COLOR_CARD_BG
        tab3_header_btn.border = ft.Border.all(1, COLOR_PRIMARY_LIGHT if curr == 2 else COLOR_CARD_BORDER)

        tab1_container.visible = (curr == 0)
        tab2_container.visible = (curr == 1)
        tab3_container.visible = (curr == 2)

    def switch_tab(tab_idx: int):
        state["active_tab"] = tab_idx
        update_tab_header_styles()
        if tab_idx == 0:
            refresh_detection_table()
        elif tab_idx == 1:
            refresh_staging_table()
        page.update()

    # =========================================================================
    # TAB 1: 🔍 SMART DETECTION & GENERATOR CONTROLS & LOGIC
    # =========================================================================

    detection_search_input = ft.TextField(
        label="Search candidate name, emp no, reason...",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )

    detection_select_all_checkbox = ft.Checkbox(
        label="Select All",
    )

    detection_counter_text = ft.Text("0 candidates selected", size=13, weight=ft.FontWeight.W_500, color=COLOR_TEXT_PRIMARY)
    detection_counter_badge = ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=COLOR_CARD_BG_HOVER,
        border_radius=8,
        border=ft.Border.all(1, COLOR_CARD_BORDER),
        content=ft.Row([
            ft.Icon(ft.Icons.PEOPLE_ALT_ROUNDED, color=COLOR_PRIMARY_LIGHT, size=18),
            detection_counter_text,
        ], spacing=6, tight=True),
    )

    btn_generate_selected_to_staging = ft.ElevatedButton(
        "⚡ Generate Selected to Staging Queue",
        icon=ft.Icons.FLASH_ON_ROUNDED,
        bgcolor=COLOR_PRIMARY,
        color=ft.Colors.WHITE,
        disabled=True,
    )

    btn_rescan_detector = secondary_button(
        "🔄 Re-scan Keka Data",
        icon=ft.Icons.REFRESH_ROUNDED,
    )

    detection_table_container = ft.Container()

    def update_detection_toolbar():
        n = len(state["selected_detected_ids"])
        detection_counter_text.value = f"{n} candidate{'s' if n != 1 else ''} selected"
        btn_generate_selected_to_staging.disabled = (n == 0)
        btn_generate_selected_to_staging.text = (
            f"⚡ Generate Selected to Staging Queue ({n})" if n > 0 else "⚡ Generate Selected to Staging Queue"
        )
        total_needs = len(state["detected_needs"])
        tab1_counter_text.value = str(total_needs)

    def make_detection_row_toggle(cid):
        def on_toggle(e):
            val = getattr(e.control, "value", False)
            if val:
                state["selected_detected_ids"].add(cid)
            else:
                state["selected_detected_ids"].discard(cid)
            update_detection_toolbar()

            # Update select all checkbox state
            filtered = get_filtered_detection_records()
            if filtered and all(r["candidate_id"] in state["selected_detected_ids"] for r in filtered):
                detection_select_all_checkbox.value = True
            else:
                detection_select_all_checkbox.value = False
            page.update()
        return on_toggle

    def make_detection_override_handler(cid):
        def on_override_change(e):
            val = getattr(e.control, "value", None) or getattr(e, "data", None)
            if val:
                state["detection_overrides"][cid] = val
        return on_override_change

    def on_detection_select_all_toggle(e):
        val = getattr(e.control, "value", False)
        filtered = get_filtered_detection_records()
        if val:
            for r in filtered:
                state["selected_detected_ids"].add(r["candidate_id"])
        else:
            for r in filtered:
                state["selected_detected_ids"].discard(r["candidate_id"])
        update_detection_toolbar()
        render_detection_table()
        page.update()

    def get_filtered_detection_records():
        records = state["detected_needs"]
        kw = (detection_search_input.value or "").strip().lower()
        if not kw:
            return records
        return [
            r for r in records
            if kw in str(r.get("name") or "").lower()
            or kw in str(r.get("employee_number") or "").lower()
            or kw in str(r.get("trigger_reason") or "").lower()
            or kw in str(r.get("suggested_doc_type") or "").lower()
        ]

    def render_detection_table():
        filtered = get_filtered_detection_records()
        if not filtered:
            detection_table_container.content = ft.Container(
                padding=30,
                alignment=ft.Alignment.CENTER,
                content=ft.Column([
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, color=COLOR_SUCCESS, size=36),
                    ft.Text("All candidate records are up to date! No pending document triggers detected.", color=COLOR_TEXT_SECONDARY, size=14),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            )
            detection_select_all_checkbox.value = False
            update_detection_toolbar()
            return

        rows = []
        for r in filtered:
            cid = r["candidate_id"]
            emp_no = r.get("employee_number") or "Not Assigned"
            cand_name = r.get("name") or f"Candidate #{cid}"
            trigger_reason = r.get("trigger_reason") or "Trigger detected"
            sugg_type = r.get("suggested_doc_type") or "offer"
            missing = r.get("missing_fields") or []

            current_override = state["detection_overrides"].get(cid, map_suggested_to_option(sugg_type))

            # Checkbox
            chk = ft.Checkbox(
                value=(cid in state["selected_detected_ids"]),
                on_change=make_detection_row_toggle(cid),
            )

            # Name & ID block
            name_cell = ft.Column([
                ft.Text(cand_name, weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
                ft.Text(f"Emp ID: {emp_no}  •  CID #{cid}", size=11, color=COLOR_TEXT_MUTED),
            ], spacing=2)

            # Trigger reason cell
            reason_cell = ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                bgcolor=COLOR_CARD_BG,
                border_radius=6,
                border=ft.Border.all(1, ft.Colors.with_opacity(0.15, COLOR_PRIMARY_LIGHT)),
                content=ft.Text(trigger_reason, size=11, color=COLOR_TEXT_SECONDARY),
                width=240,
            )

            # Suggested doc badge
            badge_cell = get_doc_badge(sugg_type)

            # Override dropdown
            override_dropdown = ft.Dropdown(
                value=current_override,
                options=[ft.dropdown.Option(val, text) for text, val in OVERRIDE_DOC_TYPE_OPTIONS],
                width=170,
                dense=True,
                content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=8,
                border_color=COLOR_CARD_BORDER,
                focused_border_color=COLOR_PRIMARY_LIGHT,
                on_change=make_detection_override_handler(cid),
            )

            # Health indicator
            if not missing:
                health_cell = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=COLOR_SUCCESS, size=14),
                        ft.Text("Ready", size=11, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS),
                    ], spacing=4, tight=True),
                    bgcolor="#064E3B",
                    border=ft.Border.all(1, "#059669"),
                    padding=ft.padding.symmetric(horizontal=6, vertical=3),
                    border_radius=6,
                )
            else:
                n_miss = len(missing)
                health_cell = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=COLOR_WARNING, size=14),
                        ft.Text(f"{n_miss} Missing", size=11, weight=ft.FontWeight.BOLD, color=COLOR_WARNING),
                    ], spacing=4, tight=True),
                    bgcolor="#78350F",
                    border=ft.Border.all(1, "#D97706"),
                    padding=ft.padding.symmetric(horizontal=6, vertical=3),
                    border_radius=6,
                    tooltip=f"Missing: {', '.join(missing)}",
                )

            # Row Action: Single Stage
            def make_single_stage_handler(c_id=cid):
                def do_single_stage(e):
                    doc_t = state["detection_overrides"].get(c_id, map_suggested_to_option(sugg_type))
                    if doc_t == "none":
                        show_message("Document type set to None. Skipping.", False)
                        return
                    res = document_staging_service.generate_draft_to_staging(
                        candidate_id=c_id,
                        document_type=doc_t,
                        preferred_format="pdf",
                    )
                    if res.get("success"):
                        show_message(f"Document draft staged for {cand_name}!", True)
                        switch_tab(1)
                    else:
                        show_message(f"Failed to stage document: {res.get('error')}", False)
                return do_single_stage

            single_stage_btn = ft.IconButton(
                icon=ft.Icons.FLASH_ON_ROUNDED,
                icon_color=COLOR_PRIMARY_LIGHT,
                tooltip="Generate Draft to Staging",
                on_click=make_single_stage_handler(),
            )

            rows.append(ft.DataRow(cells=[
                ft.DataCell(chk),
                ft.DataCell(name_cell),
                ft.DataCell(reason_cell),
                ft.DataCell(badge_cell),
                ft.DataCell(override_dropdown),
                ft.DataCell(health_cell),
                ft.DataCell(single_stage_btn),
            ]))

        if filtered and all(r["candidate_id"] in state["selected_detected_ids"] for r in filtered):
            detection_select_all_checkbox.value = True
        else:
            detection_select_all_checkbox.value = False

        detection_table = ft.DataTable(
            columns=[
                ft.DataColumn(detection_select_all_checkbox),
                ft.DataColumn(ft.Text("Employee & Candidate", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Trigger Reason", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Detected Type", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("HR Override", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Data Health", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Action", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ],
            rows=rows,
            heading_row_color=COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            border_radius=10,
            column_spacing=18,
        )

        detection_table_container.content = ft.Row([detection_table], scroll=ft.ScrollMode.AUTO)
        update_detection_toolbar()

    def refresh_detection_table():
        try:
            needs = smart_rule_detector.scan_all_candidates_for_document_needs() or []
        except Exception as ex:
            print(f"Error scanning document needs: {ex}")
            needs = []
        state["detected_needs"] = needs
        render_detection_table()

    def on_generate_selected_to_staging_clicked(e):
        sel_ids = sorted(list(state["selected_detected_ids"]))
        if not sel_ids:
            show_message("Please select at least one candidate first.", False)
            return

        btn_generate_selected_to_staging.disabled = True
        btn_generate_selected_to_staging.text = "⚡ Generating to Staging..."
        page.update()

        success_count = 0
        fail_count = 0
        err_msgs = []
        needs_map = {r["candidate_id"]: r for r in state["detected_needs"]}

        for cid in sel_ids:
            cand_rec = needs_map.get(cid, {})
            chosen_doc = state["detection_overrides"].get(
                cid, map_suggested_to_option(cand_rec.get("suggested_doc_type"))
            )
            if chosen_doc == "none":
                continue

            try:
                res = document_staging_service.generate_draft_to_staging(
                    candidate_id=cid,
                    document_type=chosen_doc,
                    preferred_format="pdf",
                )
                if res.get("success"):
                    success_count += 1
                else:
                    fail_count += 1
                    err_msgs.append(f"Cand #{cid}: {res.get('error')}")
            except Exception as ex:
                fail_count += 1
                err_msgs.append(f"Cand #{cid}: {ex}")

        state["selected_detected_ids"].clear()
        btn_generate_selected_to_staging.disabled = False
        btn_generate_selected_to_staging.text = "⚡ Generate Selected to Staging Queue"

        if fail_count == 0:
            show_message(f"Generated {success_count} draft(s) into staging queue successfully! Switched to Tab 2.", True)
        else:
            show_message(f"Generated {success_count} draft(s); {fail_count} failed. See logs.", False)

        switch_tab(1)
        refresh_staging_table()
        refresh_detection_table()
        page.update()

    # Wire Tab 1 events
    detection_search_input.on_change = lambda e: (render_detection_table(), page.update())
    detection_select_all_checkbox.on_change = on_detection_select_all_toggle
    btn_generate_selected_to_staging.on_click = on_generate_selected_to_staging_clicked
    btn_rescan_detector.on_click = lambda e: (refresh_detection_table(), show_message("Smart rule detector re-scan complete!", True), page.update())

    # Build Tab 1 Card
    tab1_card = modern_card(ft.Column([
        ft.Row([
            section_title(ft.Icons.AUTO_AWESOME_MOTION_ROUNDED, "Step 1: Automated Document Detection & Generation"),
            ft.Container(expand=True),
            btn_rescan_detector,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(height=10, color=COLOR_CARD_BORDER),
        ft.Text(
            "The smart rule engine scans active joinees, upcoming tenure/contract renewals, and separation logs. "
            "Select items to batch-generate non-consuming drafts into the Staging Hub for review.",
            size=12, color=COLOR_TEXT_SECONDARY
        ),
        ft.Row([
            detection_counter_badge,
            btn_generate_selected_to_staging,
            ft.Container(expand=True),
            detection_search_input,
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        ft.Divider(height=10, color=COLOR_CARD_BORDER),
        detection_table_container,
    ], spacing=12))

    tab1_container.content = tab1_card

    # =========================================================================
    # TAB 2: 📋 STAGING & FINAL REVIEW HUB CONTROLS & LOGIC
    # =========================================================================

    staging_status_dropdown = ft.Dropdown(
        label="Filter Status",
        value="Staged",
        options=[
            ft.dropdown.Option("Staged", "Staged (Pending Review)"),
            ft.dropdown.Option("Dispatched", "Dispatched (Sent)"),
            ft.dropdown.Option("Failed", "Failed"),
            ft.dropdown.Option("All", "All Records"),
        ],
        width=220,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )

    staging_search_input = ft.TextField(
        label="Search candidate name, email, ref #...",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )

    staging_select_all_checkbox = ft.Checkbox(
        label="Select All Staged",
    )

    staging_counter_text = ft.Text("0 drafts selected", size=13, weight=ft.FontWeight.W_500, color=COLOR_TEXT_PRIMARY)
    staging_counter_badge = ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=COLOR_CARD_BG_HOVER,
        border_radius=8,
        border=ft.Border.all(1, COLOR_CARD_BORDER),
        content=ft.Row([
            ft.Icon(ft.Icons.CHECKLIST_ROUNDED, color=COLOR_SUCCESS, size=18),
            staging_counter_text,
        ], spacing=6, tight=True),
    )

    btn_refresh_staging = secondary_button(
        "🔄 Refresh Queue",
        icon=ft.Icons.REFRESH_ROUNDED,
    )

    btn_final_go = ft.ElevatedButton(
        "🚀 Final Go: Dispatch Selected",
        icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
        bgcolor=COLOR_SUCCESS,
        color=ft.Colors.WHITE,
        disabled=True,
    )

    staging_table_container = ft.Container()

    def update_staging_toolbar():
        n = len(state["selected_staging_ids"])
        staging_counter_text.value = f"{n} draft{'s' if n != 1 else ''} selected"
        btn_final_go.disabled = (n == 0)
        btn_final_go.text = f"🚀 Final Go: Dispatch Selected ({n} Documents)" if n > 0 else "🚀 Final Go: Dispatch Selected"
        staged_count = sum(1 for r in state["staged_records"] if str(r.get("status")).lower() == "staged")
        tab2_counter_text.value = str(staged_count)

    def make_staging_row_toggle(sid):
        def on_toggle(e):
            val = getattr(e.control, "value", False)
            if val:
                state["selected_staging_ids"].add(sid)
            else:
                state["selected_staging_ids"].discard(sid)
            update_staging_toolbar()

            filtered = get_filtered_staging_records()
            if filtered and all(r["id"] in state["selected_staging_ids"] for r in filtered):
                staging_select_all_checkbox.value = True
            else:
                staging_select_all_checkbox.value = False
            page.update()
        return on_toggle

    def on_staging_select_all_toggle(e):
        val = getattr(e.control, "value", False)
        filtered = get_filtered_staging_records()
        if val:
            for r in filtered:
                state["selected_staging_ids"].add(r["id"])
        else:
            for r in filtered:
                state["selected_staging_ids"].discard(r["id"])
        update_staging_toolbar()
        render_staging_table()
        page.update()

    def make_format_toggle_handler(sid):
        def on_fmt_change(e):
            val = getattr(e.control, "value", "pdf")
            db_manager.update_staging_record(sid, preferred_format=val)
            # If toggled to PDF, ensure PDF conversion is done if missing
            if val == "pdf":
                rec = db_manager.get_staging_record_by_id(sid)
                if rec and not rec.get("pdf_file_path") and rec.get("doc_file_path"):
                    doc_path = rec["doc_file_path"]
                    pdf_dest = os.path.splitext(doc_path)[0] + ".pdf"
                    try:
                        c_ok, c_path, _ = pdf_converter_service.convert_docx_to_pdf(doc_path, pdf_dest)
                        if c_ok and c_path and os.path.exists(c_path):
                            db_manager.update_staging_record(sid, pdf_file_path=c_path)
                    except Exception:
                        pass
            show_message(f"Preferred delivery format updated to {val.upper()}.", True)
            refresh_staging_table()
            page.update()
        return on_fmt_change

    def get_filtered_staging_records():
        records = state["staged_records"]
        kw = (staging_search_input.value or "").strip().lower()
        if not kw:
            return records
        return [
            r for r in records
            if kw in str(r.get("recipient_name") or "").lower()
            or kw in str(r.get("candidate_name") or "").lower()
            or kw in str(r.get("recipient_email") or "").lower()
            or kw in str(r.get("document_type") or "").lower()
            or kw in str(r.get("reference_number") or "").lower()
        ]

    def render_staging_table():
        filtered = get_filtered_staging_records()
        if not filtered:
            status_curr = staging_status_dropdown.value or "Staged"
            staging_table_container.content = ft.Container(
                padding=30,
                alignment=ft.Alignment.CENTER,
                content=ft.Column([
                    ft.Icon(ft.Icons.RULE_FOLDER_OUTLINED, color=COLOR_TEXT_MUTED, size=36),
                    ft.Text(f"No records found with status '{status_curr}'.", color=COLOR_TEXT_SECONDARY, size=14),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            )
            staging_select_all_checkbox.value = False
            update_staging_toolbar()
            return

        rows = []
        for r in filtered:
            sid = r["id"]
            cand_id = r.get("candidate_id")
            c_name = r.get("recipient_name") or r.get("candidate_name") or f"Candidate #{cand_id}"
            emp_no = r.get("employee_number") or "Not Assigned"
            desig = r.get("applied_designation") or "-"
            dtype = r.get("document_type") or "offer"
            email = r.get("recipient_email") or ""
            warnings = r.get("discrepancy_warnings") or []
            status_val = r.get("status") or "Staged"
            pref_fmt = (r.get("preferred_format") or "pdf").lower()
            doc_file = r.get("doc_file_path")
            pdf_file = r.get("pdf_file_path")
            ref_num = r.get("reference_number") or "-"

            chk = ft.Checkbox(
                value=(sid in state["selected_staging_ids"]),
                on_change=make_staging_row_toggle(sid),
                disabled=(status_val == "Dispatched"),
            )

            # Candidate & ID
            cand_cell = ft.Column([
                ft.Text(c_name, weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
                ft.Text(f"Emp #{emp_no}  •  {desig}", size=11, color=COLOR_TEXT_MUTED),
            ], spacing=2)

            # Document badge
            doc_badge = get_doc_badge(dtype)

            # Recipient Email cell
            email_cell = ft.Text(
                email if email else "⚠️ Missing Email",
                size=12,
                color=COLOR_ERROR if not email else COLOR_TEXT_PRIMARY,
                weight=ft.FontWeight.W_500 if not email else ft.FontWeight.NORMAL,
            )

            # Data Health Pill
            if not warnings:
                health_pill = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=COLOR_SUCCESS, size=14),
                        ft.Text("✅ Ready", size=11, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS),
                    ], spacing=4, tight=True),
                    bgcolor="#064E3B",
                    border=ft.Border.all(1, "#059669"),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=6,
                )
            else:
                n_warn = len(warnings)
                health_pill = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=COLOR_WARNING, size=14),
                        ft.Text(f"⚠️ {n_warn} Issue{'s' if n_warn != 1 else ''}", size=11, weight=ft.FontWeight.BOLD, color=COLOR_WARNING),
                    ], spacing=4, tight=True),
                    bgcolor="#78350F",
                    border=ft.Border.all(1, "#D97706"),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=6,
                    tooltip="\n".join(str(w) for w in warnings),
                    on_click=lambda e, w=warnings, cn=c_name: open_warnings_dialog(cn, w),
                )

            # Format toggle
            format_dropdown = ft.Dropdown(
                value=pref_fmt,
                options=[ft.dropdown.Option("pdf", "PDF"), ft.dropdown.Option("docx", "DOCX")],
                width=95,
                dense=True,
                content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=8,
                border_color=COLOR_CARD_BORDER,
                focused_border_color=COLOR_PRIMARY_LIGHT,
                on_change=make_format_toggle_handler(sid),
                disabled=(status_val == "Dispatched"),
            )

            # Action Icons
            def make_preview_handler(p_fmt=pref_fmt, p_doc=doc_file, p_pdf=pdf_file):
                def do_preview(e):
                    target = p_pdf if (p_fmt == "pdf" and p_pdf and os.path.exists(p_pdf)) else p_doc
                    if target and os.path.exists(target):
                        open_file_safe(target)
                        show_message(f"Opening {os.path.basename(target)} in system viewer...", True)
                    else:
                        show_message("Document file is not accessible or has not been generated.", False)
                return do_preview

            def make_discard_handler(s_id=sid):
                def do_discard(e):
                    rec = db_manager.get_staging_record_by_id(s_id)
                    if rec:
                        doc_p = rec.get("doc_file_path")
                        pdf_p = rec.get("pdf_file_path")
                        for p in [doc_p, pdf_p]:
                            if p and os.path.exists(p) and "staged_" in os.path.basename(p):
                                try:
                                    os.remove(p)
                                except Exception:
                                    pass
                    db_manager.delete_staging_record(s_id)
                    state["selected_staging_ids"].discard(s_id)
                    show_message("Staged draft discarded.", True)
                    refresh_staging_table()
                    page.update()
                return do_discard

            preview_btn = ft.IconButton(
                icon=ft.Icons.VISIBILITY_ROUNDED,
                icon_color=COLOR_PRIMARY_LIGHT,
                tooltip="Preview Draft in OS Viewer",
                on_click=make_preview_handler(),
            )

            fix_btn = ft.IconButton(
                icon=ft.Icons.EDIT_ROUNDED,
                icon_color=COLOR_WARNING,
                tooltip="Fix Details & Regenerate Document",
                on_click=lambda e, s_id=sid: open_fix_details_modal(s_id),
                disabled=(status_val == "Dispatched"),
            )

            discard_btn = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                icon_color=COLOR_ERROR,
                tooltip="Discard from Staging Queue",
                on_click=make_discard_handler(),
                disabled=(status_val == "Dispatched"),
            )

            actions_cell = ft.Row([preview_btn, fix_btn, discard_btn], spacing=2)

            rows.append(ft.DataRow(cells=[
                ft.DataCell(chk),
                ft.DataCell(cand_cell),
                ft.DataCell(doc_badge),
                ft.DataCell(email_cell),
                ft.DataCell(health_pill),
                ft.DataCell(format_dropdown),
                ft.DataCell(actions_cell),
            ]))

        if filtered and all(r["id"] in state["selected_staging_ids"] for r in filtered):
            staging_select_all_checkbox.value = True
        else:
            staging_select_all_checkbox.value = False

        staging_table = ft.DataTable(
            columns=[
                ft.DataColumn(staging_select_all_checkbox),
                ft.DataColumn(ft.Text("Candidate Name & ID", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Document Type", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Recipient Email", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Data Health", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Format", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ],
            rows=rows,
            heading_row_color=COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            border_radius=10,
            column_spacing=16,
        )

        staging_table_container.content = ft.Row([staging_table], scroll=ft.ScrollMode.AUTO)
        update_staging_toolbar()

    def refresh_staging_table():
        curr_status = staging_status_dropdown.value or "Staged"
        try:
            records = db_manager.get_staging_records(status=curr_status) or []
        except Exception as ex:
            print(f"Error fetching staging records: {ex}")
            records = []
        state["staged_records"] = records
        render_staging_table()

    # Modal Dialogs for Tab 2
    def open_warnings_dialog(cand_name: str, warnings: list):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=COLOR_WARNING, size=24),
                ft.Text(f"Data Health Issues for {cand_name}", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY, size=16),
            ], spacing=8),
            content=ft.Container(
                width=450,
                content=ft.Column([
                    ft.Text("The following issues were identified during automated audit:", size=13, color=COLOR_TEXT_SECONDARY),
                    ft.Divider(height=10, color=COLOR_CARD_BORDER),
                    *[ft.Row([
                        ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=COLOR_WARNING, size=16),
                        ft.Text(str(w), size=12, color=COLOR_TEXT_PRIMARY),
                    ], spacing=6) for w in warnings],
                    ft.Container(height=6),
                    ft.Text("Tip: Click '✏️ Fix Details' on the row to correct these fields and instantly regenerate.", size=12, color=COLOR_TEXT_MUTED, italic=True),
                ], spacing=6, tight=True),
            ),
            actions=[
                ft.ElevatedButton("Close", bgcolor=COLOR_CARD_BG_HOVER, color=COLOR_TEXT_PRIMARY, on_click=lambda e: page.close(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)
        page.update()

    def open_fix_details_modal(staging_id: int):
        staging_rec = db_manager.get_staging_record_by_id(staging_id)
        if not staging_rec:
            show_message("Staging record not found.", False)
            return

        cand_id = staging_rec.get("candidate_id")
        candidate = db_manager.get_candidate_by_id(cand_id) or {}
        extra_fields = staging_rec.get("extra_fields") or {}

        name_field = ft.TextField(
            label="Candidate Full Name",
            value=str(staging_rec.get("recipient_name") or candidate.get("candidate_name") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        desig_field = ft.TextField(
            label="Applied Designation / Role",
            value=str(candidate.get("applied_designation") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        dept_field = ft.TextField(
            label="Department",
            value=str(candidate.get("department") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        loc_field = ft.TextField(
            label="Location / Full Address",
            value=str(candidate.get("full_address") or candidate.get("location") or ""),
            multiline=True,
            min_lines=2,
            max_lines=3,
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
        )
        salary_field = ft.TextField(
            label="Monthly Salary (₹)",
            value=str(candidate.get("negotiated_salary") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        relieving_field = ft.TextField(
            label="Relieving / Exit Date (YYYY-MM-DD)",
            value=str(extra_fields.get("exit_date") or candidate.get("relieving_date") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        email_field = ft.TextField(
            label="Recipient Email Address",
            value=str(staging_rec.get("recipient_email") or candidate.get("email") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )

        def on_save_fix(e):
            c_name_val = (name_field.value or "").strip()
            c_desig_val = (desig_field.value or "").strip()
            c_dept_val = (dept_field.value or "").strip()
            c_loc_val = (loc_field.value or "").strip()
            c_email_val = (email_field.value or "").strip()
            c_sal_val = (salary_field.value or "").strip()
            c_rel_val = (relieving_field.value or "").strip()

            updated_cand = {
                "candidate_name": c_name_val,
                "applied_designation": c_desig_val,
                "department": c_dept_val,
                "full_address": c_loc_val,
                "email": c_email_val,
            }
            if c_sal_val:
                try:
                    updated_cand["negotiated_salary"] = float(c_sal_val)
                except ValueError:
                    pass
            if c_rel_val:
                updated_cand["relieving_date"] = c_rel_val

            updated_extra = {}
            if c_rel_val:
                updated_extra["exit_date"] = c_rel_val

            res = document_staging_service.inline_fix_and_regenerate(
                staging_id=staging_id,
                updated_candidate_fields=updated_cand,
                updated_extra_fields=updated_extra,
            )
            page.close(dlg)
            if res.get("success"):
                show_message("Details saved and document regenerated successfully!", True)
            else:
                show_message(f"Error regenerating document: {res.get('error')}", False)
            refresh_staging_table()
            page.update()

        def on_cancel_fix(e):
            page.close(dlg)
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.EDIT_NOTE_ROUNDED, color=COLOR_PRIMARY_LIGHT, size=24),
                ft.Text(f"Fix Details & Regenerate Document (#{staging_id})", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY, size=17),
            ], spacing=8),
            content=ft.Container(
                width=580,
                content=ft.Column([
                    ft.Text(
                        "Updating these fields updates the database and instantly re-renders the draft document and AI email cover.",
                        size=12, color=COLOR_TEXT_SECONDARY
                    ),
                    ft.Divider(height=10, color=COLOR_CARD_BORDER),
                    ft.Row([name_field, email_field], spacing=10),
                    ft.Row([desig_field, dept_field], spacing=10),
                    loc_field,
                    ft.Row([salary_field, relieving_field], spacing=10),
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel_fix),
                ft.ElevatedButton(
                    "💾 Save & Regenerate Document",
                    bgcolor=COLOR_SUCCESS,
                    color=ft.Colors.WHITE,
                    on_click=on_save_fix,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)
        page.update()
        return dlg

    def open_final_go_confirmation(e=None):
        sel_ids = sorted(list(state["selected_staging_ids"]))
        if not sel_ids:
            show_message("Please select at least one staged document to dispatch.", False)
            return

        records = [db_manager.get_staging_record_by_id(sid) for sid in sel_ids]
        records = [r for r in records if r is not None]

        summary_rows = []
        for r in records:
            c_name = r.get("recipient_name") or r.get("candidate_name") or f"Candidate #{r.get('candidate_id')}"
            email = r.get("recipient_email") or "⚠️ Missing Email"
            dtype = (r.get("document_type") or "").replace("_", " ").title()
            fmt = (r.get("preferred_format") or "PDF").upper()
            summary_rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(c_name, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY)),
                ft.DataCell(ft.Text(dtype, color=COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(email, color=COLOR_ERROR if "Missing" in email else COLOR_TEXT_MUTED)),
                ft.DataCell(ft.Text(fmt, weight=ft.FontWeight.BOLD, color=COLOR_PRIMARY_LIGHT)),
            ]))

        summary_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Candidate", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Document", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Recipient Email", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Format", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ],
            rows=summary_rows,
            heading_row_color=COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            column_spacing=14,
        )

        def on_confirm_dispatch(ev):
            page.close(dlg)
            page.update()
            execute_final_go(sel_ids)

        def on_cancel_dispatch(ev):
            page.close(dlg)
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED, color=COLOR_SUCCESS, size=26),
                ft.Text(f"Final Go: Dispatch {len(records)} Document(s)", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY, size=18),
            ], spacing=10),
            content=ft.Container(
                width=640,
                content=ft.Column([
                    ft.Text(
                        "You are about to consume official sequence numbers (e.g. DFY/HR/...) "
                        "and immediately dispatch emails to each recipient with their final document attachment.",
                        size=13, color=COLOR_TEXT_SECONDARY
                    ),
                    ft.Divider(height=10, color=COLOR_CARD_BORDER),
                    ft.Row([summary_table], scroll=ft.ScrollMode.AUTO),
                    ft.Divider(height=10, color=COLOR_CARD_BORDER),
                    ft.Container(
                        bgcolor=ft.Colors.with_opacity(0.12, COLOR_WARNING),
                        padding=10,
                        border_radius=8,
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.3, COLOR_WARNING)),
                        content=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, color=COLOR_WARNING, size=18),
                            ft.Text("This action is permanent and consumes official reference numbers.", size=12, color=COLOR_WARNING),
                        ], spacing=8),
                    ),
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel_dispatch),
                ft.ElevatedButton(
                    f"🚀 Confirm & Dispatch All ({len(records)})",
                    bgcolor=COLOR_SUCCESS,
                    color=ft.Colors.WHITE,
                    on_click=on_confirm_dispatch,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)
        page.update()
        return dlg

    def execute_final_go(staging_ids: list):
        show_message("Executing Final Go bulk dispatch...", True)

        res = document_staging_service.final_go_dispatch(staging_ids, send_async=False)

        total = res.get("total", len(staging_ids))
        sent = res.get("sent", 0)
        failed = res.get("failed", 0)
        errors = res.get("errors", [])

        state["selected_staging_ids"].clear()
        refresh_staging_table()

        report_items = [
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLOR_SUCCESS, size=24),
                ft.Text(f"Successfully Sent: {sent} document(s)", size=14, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS),
            ], spacing=8),
            ft.Row([
                ft.Icon(ft.Icons.ERROR if failed > 0 else ft.Icons.CHECK_CIRCLE, color=COLOR_ERROR if failed > 0 else COLOR_TEXT_MUTED, size=24),
                ft.Text(f"Failed: {failed} document(s)", size=14, weight=ft.FontWeight.BOLD, color=COLOR_ERROR if failed > 0 else COLOR_TEXT_MUTED),
            ], spacing=8),
        ]

        if errors:
            error_controls = [ft.Text(f"• {err}", size=12, color=COLOR_ERROR) for err in errors[:10]]
            report_items.extend([
                ft.Divider(height=10, color=COLOR_CARD_BORDER),
                ft.Text("Errors Encountered:", weight=ft.FontWeight.BOLD, size=13, color=COLOR_ERROR),
                *error_controls,
            ])

        def close_report(ev):
            page.close(report_dlg)
            page.update()

        report_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.TASK_ALT_ROUNDED, color=COLOR_SUCCESS if failed == 0 else COLOR_WARNING, size=26),
                ft.Text("Bulk Dispatch Report", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY, size=18),
            ], spacing=10),
            content=ft.Container(
                width=500,
                content=ft.Column(report_items, spacing=8, tight=True, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.ElevatedButton("Close", bgcolor=COLOR_PRIMARY_LIGHT, color=ft.Colors.WHITE, on_click=close_report),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(report_dlg)
        page.update()
        return report_dlg

    # Wire Tab 2 events
    staging_status_dropdown.on_change = lambda e: (refresh_staging_table(), page.update())
    staging_search_input.on_change = lambda e: (render_staging_table(), page.update())
    staging_select_all_checkbox.on_change = on_staging_select_all_toggle
    btn_refresh_staging.on_click = lambda e: (refresh_staging_table(), show_message("Staging queue refreshed!", True), page.update())
    btn_final_go.on_click = open_final_go_confirmation

    # Build Tab 2 Card
    tab2_card = modern_card(ft.Column([
        ft.Row([
            section_title(ft.Icons.FACT_CHECK_ROUNDED, "Step 2: Staged Drafts Review & Final Go Bulk Dispatch"),
            ft.Container(expand=True),
            btn_refresh_staging,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(height=10, color=COLOR_CARD_BORDER),
        ft.Text(
            "Review draft documents in OS viewer (Word/PDF). Use '✏️ Fix Details' for instant corrections with document regeneration. "
            "When fully satisfied, click '🚀 Final Go' to atomically consume reference numbers and transmit via email.",
            size=12, color=COLOR_TEXT_SECONDARY
        ),
        ft.Row([
            staging_counter_badge,
            staging_status_dropdown,
            ft.Container(expand=True),
            staging_search_input,
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        ft.Divider(height=10, color=COLOR_CARD_BORDER),
        staging_table_container,
        ft.Divider(height=10, color=COLOR_CARD_BORDER),
        # Bottom Final Go Action Bar
        ft.Container(
            padding=14,
            border_radius=10,
            bgcolor=COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            content=ft.Row([
                ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED, color=COLOR_SUCCESS, size=24),
                ft.Column([
                    ft.Text("Human-in-the-Loop Quality Gate", weight=ft.FontWeight.BOLD, size=14, color=COLOR_TEXT_PRIMARY),
                    ft.Text("Reference numbers will only be consumed upon final dispatch.", size=12, color=COLOR_TEXT_SECONDARY),
                ], spacing=2, expand=True),
                btn_final_go,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ),
    ], spacing=12))

    tab2_container.content = tab2_card

    # =========================================================================
    # TAB 3: ✍️ MANUAL ONE-OFF GENERATOR (Retained & Enhanced)
    # =========================================================================

    candidate_dropdown = ft.Dropdown(
        label="Select Candidate",
        expand=True,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )

    search_text = ft.TextField(
        label="Search candidate (Name or Mobile)...",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )

    candidate_info_container = ft.Container(visible=False)

    doc_type_dropdown = ft.Dropdown(
        label="Document Type",
        value="offer",
        options=[ft.dropdown.Option(val, text) for text, val in DOC_TYPE_OPTIONS],
        width=300,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )

    father_name_field = ft.TextField(
        label="Father's Name", expand=True, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    gender_dropdown = ft.Dropdown(
        label="Gender",
        options=[ft.dropdown.Option("Male"), ft.dropdown.Option("Female"), ft.dropdown.Option("Other")],
        width=150,
        border_radius=8,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )
    address_field = ft.TextField(
        label="Full Address (comma separated)", multiline=True, min_lines=2, max_lines=3,
        expand=True, border_radius=8, border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    department_field = ft.TextField(
        label="Department", width=220, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    date_joined_field = ft.TextField(
        label="Date Joined (YYYY-MM-DD)", width=200, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    salary_field = ft.TextField(
        label="Negotiated Monthly Salary (₹)", width=220, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    employee_number_field = ft.TextField(
        label="Employee Number", width=200, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )

    ext_start_date_field = ft.TextField(
        label="Extension Start Date (YYYY-MM-DD)", width=250, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    term_date_field = ft.TextField(
        label="Termination Date (YYYY-MM-DD)", width=220, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    term_notice_field = ft.TextField(
        label="Notice Period (e.g. 30 Days)", width=200, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    term_reason_field = ft.TextField(
        label="Termination Reason", multiline=True, min_lines=2, expand=True, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    inc_effective_field = ft.TextField(
        label="Effective From Date (YYYY-MM-DD)", width=220, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    inc_revised_salary_field = ft.TextField(
        label="Revised Monthly Salary (₹)", width=220, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    inc_offer_doc_date_field = ft.TextField(
        label="Offer Letter Document Date (YYYY-MM-DD)", width=250, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    cert_exit_date_field = ft.TextField(
        label="Exit / Relieving Date (leave blank if currently working)", width=320, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )

    dynamic_fields_container = ft.Container()
    template_override_container = ft.Container(visible=False)
    result_container = ft.Container()
    history_container = ft.Container()
    email_history_container = ft.Container()

    def load_candidates_into_dropdown(filter_text=""):
        candidates = db_manager.get_all_candidates(search_term=filter_text)
        options = []
        for c in candidates:
            c_name = c.get("candidate_name") or "Unnamed"
            c_mob = c.get("mobile") or "No Mobile"
            c_desig = c.get("applied_designation") or "No Role"
            options.append(ft.dropdown.Option(str(c["id"]), f"{c_name} ({c_mob}) - {c_desig}"))
        candidate_dropdown.options = options
        if not options:
            candidate_dropdown.value = None

    def refresh_candidate_info_card(cand):
        if not cand:
            candidate_info_container.visible = False
            candidate_info_container.content = None
            return

        candidate_info_container.visible = True
        c_name = cand.get("candidate_name") or "-"
        c_mob = cand.get("mobile") or "-"
        c_desig = cand.get("applied_designation") or "-"
        c_status = cand.get("status") or "-"
        c_emp = cand.get("employee_number") or "Not Assigned"

        candidate_info_container.content = ft.Container(
            bgcolor=COLOR_CARD_BG_HOVER,
            padding=14,
            border_radius=10,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.PERSON_PIN_ROUNDED, color=COLOR_PRIMARY_LIGHT, size=24),
                    padding=8,
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.15, COLOR_PRIMARY_LIGHT),
                ),
                ft.Column([
                    ft.Text(f"{c_name}  •  {c_desig}", weight=ft.FontWeight.BOLD, size=15, color=COLOR_TEXT_PRIMARY),
                    ft.Text(f"Mobile: {c_mob}  |  Status: {c_status}  |  Employee ID: {c_emp}", size=12, color=COLOR_TEXT_SECONDARY),
                ], spacing=2, expand=True),
            ], spacing=12),
        )

    def populate_form_from_candidate(cand):
        if not cand:
            return
        father_name_field.value = cand.get("father_name") or ""
        gender_dropdown.value = cand.get("gender") if cand.get("gender") in ["Male", "Female", "Other"] else "Male"
        address_field.value = cand.get("full_address") or ""
        department_field.value = cand.get("department") or ""
        date_joined_field.value = cand.get("date_joined") or ""
        salary_field.value = str(cand.get("negotiated_salary") or "")
        employee_number_field.value = cand.get("employee_number") or ""
        cert_exit_date_field.value = cand.get("relieving_date") or ""

    def save_candidate_edits():
        cid = state["selected_candidate_id"]
        if not cid:
            return
        db_manager.update_candidate_extra_details(
            candidate_id=cid,
            father_name=father_name_field.value.strip(),
            full_address=address_field.value.strip(),
            gender=gender_dropdown.value or "Male",
            department=department_field.value.strip(),
            date_joined=date_joined_field.value.strip(),
            employee_number=employee_number_field.value.strip(),
        )
        state["selected_candidate"] = db_manager.get_candidate_by_id(cid)

    def collect_extra_fields():
        doc_type = state["selected_doc_type"]
        extra = {}
        if doc_type == "extension":
            extra["extension_start_date"] = ext_start_date_field.value.strip()
        elif doc_type == "increment":
            extra["effective_from"] = inc_effective_field.value.strip()
            extra["revised_pay_grade"] = inc_revised_salary_field.value.strip()
            extra["offer_letter_document_date"] = inc_offer_doc_date_field.value.strip()
        elif doc_type == "termination":
            extra["termination_date"] = term_date_field.value.strip()
            extra["notice_period"] = term_notice_field.value.strip()
            extra["reason"] = term_reason_field.value.strip()
        elif doc_type in ["experience", "salary"]:
            exit_val = cert_exit_date_field.value.strip()
            extra["exit_date"] = exit_val if exit_val else None
        return extra

    def update_dynamic_fields():
        doc_type = state["selected_doc_type"]
        if doc_type == "offer":
            dynamic_fields_container.content = ft.Text(
                "ℹ️ Offer letters use base candidate details and negotiated monthly salary.",
                size=12, color=COLOR_TEXT_SECONDARY, italic=True
            )
        elif doc_type == "extension":
            dynamic_fields_container.content = ft.Column([
                ft.Text("Extension Period Details", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
                ft.Row([ext_start_date_field], spacing=12),
            ], spacing=6)
        elif doc_type == "increment":
            dynamic_fields_container.content = ft.Column([
                ft.Text("Increment Event Details", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
                ft.Row([inc_effective_field, inc_revised_salary_field, inc_offer_doc_date_field], spacing=12),
            ], spacing=6)
        elif doc_type == "termination":
            dynamic_fields_container.content = ft.Column([
                ft.Text("Termination Event Details", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
                ft.Row([term_date_field, term_notice_field], spacing=12),
                term_reason_field,
            ], spacing=6)
        elif doc_type in ["experience", "salary"]:
            cert_name = "Experience Certificate" if doc_type == "experience" else "Salary Certificate"
            dynamic_fields_container.content = ft.Column([
                ft.Text(f"{cert_name} Details", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
                ft.Row([cert_exit_date_field], spacing=12),
                ft.Text(
                    "💡 If left blank, the certificate will state that the employee 'is currently working' up to Till Date.",
                    size=12, color=COLOR_TEXT_SECONDARY, italic=True
                ),
            ], spacing=6)
        page.update()

    def check_template_availability():
        cid = state["selected_candidate_id"]
        doc_type = state["selected_doc_type"]
        if not cid:
            template_override_container.visible = False
            return

        cand = state["selected_candidate"]
        res = document_generation_service.resolve_template(
            doc_type, cand, state["manual_override_desig"]
        )

        if not res.get("found"):
            avail = res.get("available_designations", [])
            override_dropdown = ft.Dropdown(
                label="Choose Matching Template",
                options=[ft.dropdown.Option(d) for d in avail],
                width=350,
                border_radius=8,
                border_color=COLOR_CARD_BORDER,
                focused_border_color=COLOR_PRIMARY_LIGHT,
                on_select=lambda e: set_manual_override(getattr(e.control, "value", None) or getattr(e, "data", None)),
            )
            cand_desig = cand.get("applied_designation") or "Unspecified"
            template_override_container.visible = True
            template_override_container.content = ft.Container(
                bgcolor=ft.Colors.ORANGE_900,
                padding=12,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.ORANGE_700),
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.ORANGE_200, size=20),
                        ft.Text(
                            f"We couldn't find an exact template match for '{cand_desig}'. "
                            "Please choose one manually below:",
                            color=ft.Colors.WHITE, size=13, weight=ft.FontWeight.W_500
                        ),
                    ], spacing=8),
                    override_dropdown,
                ], spacing=8),
            )
        else:
            template_override_container.visible = False
            template_override_container.content = None

    def set_manual_override(desig):
        state["manual_override_desig"] = desig
        page.update()

    def refresh_history_table():
        cid = state["selected_candidate_id"]
        if not cid:
            history_container.visible = False
            return

        history = db_manager.get_generation_history(cid)
        if not history:
            history_container.visible = True
            history_container.content = modern_card(ft.Column([
                section_title(ft.Icons.HISTORY_ROUNDED, "Recent Documents for this Candidate"),
                ft.Divider(height=10, color=COLOR_CARD_BORDER),
                ft.Text("No documents have been generated for this candidate yet.", size=13, color=COLOR_TEXT_SECONDARY),
            ], spacing=8))
            page.update()
            return

        rows = []
        for h in history:
            doc_type_cap = (h.get("document_type") or "").replace("_", " ").title()
            ref_num = h.get("reference_number") or "-"
            gen_date = h.get("generated_date") or "-"
            fpath = h.get("file_path") or ""

            action_btn = ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                icon_color=COLOR_PRIMARY_LIGHT,
                tooltip="Open Generated Document",
                on_click=lambda e, fp=fpath: open_file_safe(fp),
            )
            email_btn = ft.IconButton(
                icon=ft.Icons.EMAIL_OUTLINED,
                icon_color=COLOR_SUCCESS,
                tooltip="Send Document via Email",
                on_click=lambda e, dt=h.get("document_type"), rn=ref_num, fp=fpath: open_email_preview_flow(
                    state["selected_candidate"], dt, rn, fp
                ),
            )

            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(doc_type_cap, weight=ft.FontWeight.W_500, color=COLOR_TEXT_PRIMARY)),
                ft.DataCell(ft.Text(ref_num, color=COLOR_SUCCESS, weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(gen_date, size=12, color=COLOR_TEXT_MUTED)),
                ft.DataCell(ft.Row([action_btn, email_btn], spacing=4)),
            ]))

        history_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Document Type", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Reference Number", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Generated Date", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ],
            rows=rows,
            heading_row_color=COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            border_radius=10,
            column_spacing=24,
        )

        def export_history_clicked(e):
            out_path = os.path.join(DESKTOP_APP_DIR, "output", f"candidate_{cid}_documents_history.xlsx")
            export_data = [
                {
                    "Document Type": r.get("document_type", ""),
                    "Reference Number": r.get("reference_number", ""),
                    "Generated Date": r.get("generated_date", ""),
                    "File Path": r.get("file_path", ""),
                }
                for r in history
            ]
            excel_export_service.export_to_excel(export_data, out_path, sheet_name="Documents")
            show_message(f"Document history exported to {os.path.basename(out_path)}!", True)

        history_container.visible = True
        history_container.content = modern_card(ft.Column([
            ft.Row([
                section_title(ft.Icons.HISTORY_ROUNDED, "Recent Documents for this Candidate"),
                ft.Container(expand=True),
                secondary_button(
                    "Export History to Excel",
                    icon=ft.Icons.DOWNLOAD_ROUNDED,
                    on_click=export_history_clicked,
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Row([history_table], scroll=ft.ScrollMode.AUTO),
        ], spacing=10))
        page.update()

    def refresh_email_logs_for_candidate():
        cid = state["selected_candidate_id"]
        if not cid:
            email_history_container.visible = False
            return

        logs = db_manager.get_email_logs(candidate_id=cid)
        if not logs:
            email_history_container.visible = False
            page.update()
            return

        def export_cand_email_history(e):
            out_path = os.path.join(DESKTOP_APP_DIR, "output", f"candidate_{cid}_email_log.xlsx")
            export_data = [
                {
                    "Date & Time": r.get("timestamp", ""),
                    "Recipient Email": r.get("recipient_email", ""),
                    "Document Type": (r.get("document_type") or "").replace("_", " ").title(),
                    "Subject": r.get("subject", ""),
                    "Attachment": r.get("attachment_filename", ""),
                    "Status": r.get("status", ""),
                    "Sent By": r.get("sent_by", ""),
                    "Error Details": r.get("error_message") or "",
                }
                for r in logs
            ]
            excel_export_service.export_to_excel(export_data, out_path, sheet_name="Email Log")
            show_message(f"Candidate email log exported to {os.path.basename(out_path)}!", True)

        table_rows = []
        for r in logs:
            is_ok = r.get("status") == "Success"
            badge = status_badge("Success") if is_ok else status_badge("Failed")
            table_rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(r.get("timestamp", "-"), size=12, color=COLOR_TEXT_MUTED)),
                ft.DataCell(ft.Text(r.get("recipient_email", "-"), color=COLOR_TEXT_PRIMARY)),
                ft.DataCell(ft.Text((r.get("document_type") or "-").replace("_", " ").title(), color=COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(r.get("attachment_filename") or "-", size=12, color=COLOR_TEXT_MUTED)),
                ft.DataCell(badge),
            ]))

        dt = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Date & Time", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Recipient Email", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Document Type", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Attachment", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ],
            rows=table_rows,
            heading_row_color=COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            border_radius=10,
            column_spacing=18,
        )

        email_history_container.visible = True
        email_history_container.content = modern_card(ft.Column([
            ft.Row([
                section_title(ft.Icons.MARK_EMAIL_READ_ROUNDED, "Email Dispatch History for this Candidate"),
                ft.Container(expand=True),
                secondary_button("Export Email Log to Excel", icon=ft.Icons.DOWNLOAD_ROUNDED, on_click=export_cand_email_history),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Row([dt], scroll=ft.ScrollMode.AUTO),
        ], spacing=10))
        page.update()

    def on_search_change(e):
        load_candidates_into_dropdown(filter_text=e.control.value)
        page.update()

    def on_candidate_selected(e):
        val = getattr(e.control, "value", None) or getattr(e, "data", None)
        if not val:
            state["selected_candidate_id"] = None
            state["selected_candidate"] = None
            refresh_candidate_info_card(None)
            page.update()
            return

        try:
            cid = int(val)
        except (ValueError, TypeError):
            return

        state["selected_candidate_id"] = cid
        cand = db_manager.get_candidate_by_id(cid)
        state["selected_candidate"] = cand
        state["manual_override_desig"] = None
        state["preview_generated"] = False
        result_container.content = None

        refresh_candidate_info_card(cand)
        populate_form_from_candidate(cand)
        check_template_availability()
        refresh_history_table()
        refresh_email_logs_for_candidate()
        page.update()

    def on_doc_type_change(e):
        val = getattr(e.control, "value", None) or getattr(e, "data", None)
        if val:
            state["selected_doc_type"] = val
        state["manual_override_desig"] = None
        state["preview_generated"] = False
        result_container.content = None
        update_dynamic_fields()
        check_template_availability()
        page.update()

    def open_email_preview_flow(candidate: dict, doc_type: str, ref_num: str, file_path: str):
        if not candidate:
            show_message("Please select a candidate first.", False)
            return

        open_email_preview_modal(
            page=page,
            candidate=candidate,
            document_type=doc_type,
            attachment_path=file_path,
            on_dispatch_complete=refresh_email_logs_for_candidate,
        )

    def on_preview_clicked(e):
        cid = state["selected_candidate_id"]
        if not cid:
            show_message("Please select a candidate first.", False)
            return

        save_candidate_edits()
        extra = collect_extra_fields()

        res = document_generation_service.generate_preview_document(
            candidate_id=cid,
            document_type=state["selected_doc_type"],
            extra_fields=extra,
            manual_designation_override=state["manual_override_desig"]
        )

        if not res.get("success"):
            if res.get("needs_template_selection"):
                check_template_availability()
            err = res.get("error", "Failed to generate preview.")
            result_container.content = ft.Container(
                bgcolor=ft.Colors.RED_900,
                padding=14,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.RED_700),
                content=ft.Row([
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_200, size=24),
                    ft.Text(err, color=ft.Colors.WHITE, size=13),
                ], spacing=10),
            )
            show_message(err, False)
        else:
            state["preview_generated"] = True
            state["last_preview_path"] = res["preview_file_path"]
            preview_ref = res.get("previewed_reference_number", "-")

            result_container.content = ft.Container(
                bgcolor=COLOR_CARD_BG_HOVER,
                padding=16,
                border_radius=10,
                border=ft.Border.all(1, COLOR_PRIMARY_LIGHT),
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.VISIBILITY_ROUNDED, color=COLOR_PRIMARY_LIGHT, size=24),
                        ft.Column([
                            ft.Text("Preview Ready!", size=15, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS),
                            ft.Text(f"Estimated Reference Number (not yet assigned): {preview_ref}", size=12, color=COLOR_TEXT_SECONDARY),
                        ], spacing=2, expand=True),
                        primary_button(
                            "Open Preview in Word",
                            icon=ft.Icons.DESCRIPTION_ROUNDED,
                            on_click=lambda ev: open_file_safe(state["last_preview_path"]),
                        ),
                    ], spacing=12),
                    ft.Text(
                        "ℹ️ Preview generated successfully. No reference number was consumed from your sequence.",
                        size=12, color=COLOR_TEXT_SECONDARY, italic=True
                    ),
                ], spacing=8),
            )
            show_message("Preview ready! Check the Word document.", True)

        page.update()

    def on_stage_one_off_clicked(e):
        cid = state["selected_candidate_id"]
        if not cid:
            show_message("Please select a candidate first.", False)
            return

        save_candidate_edits()
        extra = collect_extra_fields()

        res = document_staging_service.generate_draft_to_staging(
            candidate_id=cid,
            document_type=state["selected_doc_type"],
            extra_fields=extra,
            preferred_format="pdf",
            manual_designation_override=state["manual_override_desig"],
        )

        if res.get("success"):
            show_message("One-off document draft sent to Staging Hub! Switched to Tab 2.", True)
            switch_tab(1)
            refresh_staging_table()
        else:
            show_message(f"Could not stage document: {res.get('error')}", False)
        page.update()

    def on_finalize_clicked(e):
        cid = state["selected_candidate_id"]
        if not cid:
            show_message("Please select a candidate first.", False)
            return

        save_candidate_edits()
        extra = collect_extra_fields()

        res = document_generation_service.finalize_document(
            candidate_id=cid,
            document_type=state["selected_doc_type"],
            extra_fields=extra,
            manual_designation_override=state["manual_override_desig"]
        )

        if not res.get("success"):
            err = res.get("error", "Failed to generate final document.")
            result_container.content = ft.Container(
                bgcolor=ft.Colors.RED_900,
                padding=14,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.RED_700),
                content=ft.Row([
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_200, size=24),
                    ft.Text(err, color=ft.Colors.WHITE, size=13),
                ], spacing=10),
            )
            show_message(err, False)
        else:
            state["last_final_path"] = res["file_path"]
            final_ref = res.get("reference_number", "-")
            file_name = os.path.basename(res["file_path"])

            result_container.content = ft.Container(
                bgcolor=COLOR_CARD_BG_HOVER,
                padding=16,
                border_radius=10,
                border=ft.Border.all(1, COLOR_SUCCESS),
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=COLOR_SUCCESS, size=28),
                        ft.Column([
                            ft.Text("Final Document Generated Successfully! 🎉", size=16, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS),
                            ft.Text(f"Assigned Reference Number: {final_ref}", size=13, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                            ft.Text(f"Saved File: {file_name}", size=12, color=COLOR_TEXT_SECONDARY),
                        ], spacing=2, expand=True),
                        ft.Row([
                            ft.ElevatedButton(
                                "Open Document",
                                icon=ft.Icons.DESCRIPTION_ROUNDED,
                                bgcolor=ft.Colors.GREEN_700,
                                color=ft.Colors.WHITE,
                                on_click=lambda ev: open_file_safe(state["last_final_path"]),
                            ),
                            secondary_button(
                                "Open Folder",
                                icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                                on_click=lambda ev: open_file_safe(os.path.dirname(state["last_final_path"])),
                            ),
                            ft.ElevatedButton(
                                "Send via Email",
                                icon=ft.Icons.EMAIL_ROUNDED,
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE,
                                on_click=lambda ev: open_email_preview_flow(
                                    state["selected_candidate"],
                                    state["selected_doc_type"],
                                    final_ref,
                                    state["last_final_path"]
                                ),
                            ),
                        ], spacing=8),
                    ], spacing=12),
                ], spacing=8),
            )
            show_message(f"Document finalized with Reference #{final_ref}!", True)
            refresh_history_table()
            refresh_email_logs_for_candidate()

        page.update()

    # Wire Tab 3 events
    search_text.on_change = on_search_change
    candidate_dropdown.on_select = on_candidate_selected
    candidate_dropdown.on_change = on_candidate_selected
    doc_type_dropdown.on_select = on_doc_type_change
    doc_type_dropdown.on_change = on_doc_type_change

    # Build Tab 3 Card
    tab3_card = ft.Column([
        modern_card(ft.Column([
            section_title(ft.Icons.BADGE_ROUNDED, "Step 1: Select Candidate & Document Type"),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Row([search_text, candidate_dropdown], spacing=12),
            candidate_info_container,
            ft.Row([doc_type_dropdown], spacing=12),
        ], spacing=12)),
        ft.Container(height=10),
        modern_card(ft.Column([
            section_title(ft.Icons.EDIT_NOTE_ROUNDED, "Step 2: Review & Fill Document Details"),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Text(
                "These details pre-fill from the candidate record. Any corrections you make here will be saved back to the database.",
                size=12, color=COLOR_TEXT_SECONDARY
            ),
            ft.Row([father_name_field, gender_dropdown, department_field], spacing=12),
            address_field,
            ft.Row([date_joined_field, salary_field, employee_number_field], spacing=12),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            dynamic_fields_container,
            template_override_container,
        ], spacing=12)),
        ft.Container(height=10),
        modern_card(ft.Column([
            section_title(ft.Icons.PRINT_ROUNDED, "Step 3: Preview, Stage, or Confirm Final Generation"),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Row([
                ft.ElevatedButton(
                    "👁️ Preview Document (Safe)",
                    icon=ft.Icons.VISIBILITY_ROUNDED,
                    bgcolor=ft.Colors.BLUE_GREY_700,
                    color=ft.Colors.WHITE,
                    on_click=on_preview_clicked,
                ),
                ft.ElevatedButton(
                    "⚡ Stage Draft for Review",
                    icon=ft.Icons.RULE_FOLDER_ROUNDED,
                    bgcolor=COLOR_PRIMARY,
                    color=ft.Colors.WHITE,
                    on_click=on_stage_one_off_clicked,
                ),
                ft.ElevatedButton(
                    "✅ Confirm & Generate Final Document",
                    icon=ft.Icons.CHECK_CIRCLE_ROUNDED,
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE,
                    on_click=on_finalize_clicked,
                ),
            ], spacing=12),
            result_container,
        ], spacing=12)),
        ft.Container(height=10),
        history_container,
        email_history_container,
    ], spacing=12)

    tab3_container.content = tab3_card

    # =========================================================================
    # INITIAL DATA LOAD & VIEW ASSEMBLY
    # =========================================================================

    load_candidates_into_dropdown()
    update_dynamic_fields()
    refresh_detection_table()
    refresh_staging_table()
    update_tab_header_styles()

    view_column = ft.Column([
        # Header
        page_header(
            icon=ft.Icons.DESCRIPTION_ROUNDED,
            title="📄 Smart Document Pipeline & Staging Hub",
            subtitle="Automated document triggers, safe draft generation, human-in-the-loop review, and atomic bulk dispatch.",
        ),
        ft.Container(height=8),

        # Modern Nav Switcher
        tab_switcher_row,
        ft.Container(height=10),

        # Active Tab Containers
        tab1_container,
        tab2_container,
        tab3_container,

        ft.Container(height=20),
    ], scroll=ft.ScrollMode.AUTO, spacing=10, expand=True)

    # Expose state and key controls for testability
    view_column.state = state
    view_column.switch_tab = switch_tab
    view_column.refresh_detection_table = refresh_detection_table
    view_column.refresh_staging_table = refresh_staging_table
    view_column.btn_generate_selected_to_staging = btn_generate_selected_to_staging
    view_column.btn_final_go = btn_final_go
    view_column.btn_rescan_detector = btn_rescan_detector
    view_column.btn_refresh_staging = btn_refresh_staging
    view_column.open_fix_details_modal = open_fix_details_modal
    view_column.open_final_go_confirmation = open_final_go_confirmation
    view_column.tab1_container = tab1_container
    view_column.tab2_container = tab2_container
    view_column.tab3_container = tab3_container

    if initial_tab in (1, 2):
        switch_tab(initial_tab)

    return view_column
