"""
Page: help_center_page.py
Purpose: Dedicated Help Center, Workflow Knowledge Hub & Interactive Hinglish AI Chatbot for Doctors For You HRMS.
Designed specifically for non-technical HR managers and field coordinators.

Architecture:
- Tab 1: 🤖 DFY AI Chatbot (Interactive Hinglish assistant, 100% offline, dedicated distraction-free view).
- Tab 2: 📚 Workflow Guides & FAQs (Questions, step-by-step guides with 1-click screen navigation & instant live search).
"""

import os
import json
from typing import Optional, Callable, List, Dict, Any
import flet as ft

from config import PRIMARY_COLOR, ASSETS_DIR
from utils import ui_theme
from services import ai_copilot_service
from services import dfy_policy_service

HELP_GUIDE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "knowledge",
    "app_help_guide.json"
)

FAQS_DATA = [
    {
        "id": "faq_duplicates",
        "category": "Candidate Hiring",
        "question": "Excel upload karte waqt duplicate candidates ka warning aaye to kya karein?",
        "answer": (
            "System uploaded sheet me se existing candidates ko phone number aur email ke basis par pehchanta hai.\n\n"
            "• **✓ Keep Existing**: Agar purana record database me bilkul safe rakhna hai to 'Keep' chunein.\n"
            "• **✓ Replace with New**: Agar candidate ka salary ya designation nayi sheet ke mutabiq update karna hai to 'Replace' chunein.\n"
            "• **>50% Duplicates Alert**: Agar 50% se zyada duplicate hain to alert screen aati hai jahan aap 1-click me 'Keep All' ya individual review chun sakte hain."
        ),
        "query": "Duplicate candidate warning ka kya karein?",
    },
    {
        "id": "faq_reference_number",
        "category": "Document Staging",
        "question": "Draft document banate waqt official Reference Number consume kyu nahi hota?",
        "answer": (
            "DFY HRMS strict sequential audit compliance follow karta hai.\n\n"
            "• Draft generation ke dauran temporary draft identifier rehta hai taaki testing ya correction me official sequence kharab na ho.\n"
            "• Jab HR manager Staging Hub (Tab 2) me review complete karke **'🚀 Final Go: Dispatch Selected'** dabata hai, sirf usi waqt official atomic sequence number (e.g. `DFY/HR/2026/205`) consume aur dispatch hota hai."
        ),
        "query": "Draft banate waqt reference number consume kyu nahi hota?",
    },
    {
        "id": "faq_welcome_email",
        "category": "Joining & Onboarding",
        "question": "Official Welcome Email kab aur kin candidates ko bhejna chahiye?",
        "answer": (
            "Jab kisi candidate ka interview complete ho jaye aur panel unhe **'Selected'** status mark kare:\n\n"
            "1. Joining Process page me jayein aur **'🎉 Selected (Pending Welcome Email)'** filter tab par click karein.\n"
            "2. Candidate select karein aur top right me **'✉️ Review & Send Welcome Emails'** button dabayein.\n"
            "3. Preview modal me candidate ka naam, post aur congratulatory text check karke Send karein."
        ),
        "query": "Welcome email kab aur kaise bhejein?",
    },
    {
        "id": "faq_inline_fix",
        "category": "Document Staging",
        "question": "Staged document me agar salary ya designation galat ho to bina naye draft ke kaise theek karein?",
        "answer": (
            "Aapko document dubara shuru se generate karne ki bilkul zaroorat nahi hai!\n\n"
            "1. Document Generator ke **Tab 2 (Staging & Final Review Hub)** me jayein.\n"
            "2. Candidate ke draft card par **'✏️ Fix Details & Regenerate'** button dabayein.\n"
            "3. Dialog me sahi Salary ya Designation enter karke Save karein.\n"
            "4. System instant (1 second ke andar) document aur PDF ko auto-regenerate kar deta hai."
        ),
        "query": "Staged document me salary kaise fix karein?",
    },
    {
        "id": "faq_keka_sync",
        "category": "Keka HRMS Sync",
        "question": "Keka Sync me duplicate employee number aane par kya conflict resolution hota hai?",
        "answer": (
            "Keka Flow me employee ID hamesha unique hoti hai.\n\n"
            "• Agar same employee ID wali sheet dobara upload hoti hai, to system interactive warning dialog deta hai.\n"
            "• Aap **'🔄 Update Existing Record'** chun sakte hain nayi sheet ke data se update karne ke liye, ya **'🛡️ Keep Database Record'** chun kar incoming duplicate ko skip kar sakte hain."
        ),
        "query": "Keka sheet re-upload karne par duplicate kaise handle karein?",
    },
    {
        "id": "faq_leave_rules",
        "category": "DFY HR Manual (Art. 4)",
        "question": "DFY HR Manual 2025 ke mutabiq Casual aur Sick Leave ke kya rules hain?",
        "answer": (
            "DFY HR Manual Article 4 ke anusar:\n\n"
            "• **Casual Leave (CL)**: Urgent personal emergency ke liye supervisor ki prior written approval se milti hai.\n"
            "• **Sick Leave (SL)**: Medical illness ke liye. 2 din se zyada bimar hone par medical certificate submit karna mandatory hai.\n"
            "• **Maternity Leave**: Eligible female employees ke liye statutory provisions ke mutabiq uplabdh hai.\n"
            "• **Working Hours**: Mon to Sat subah 9:30 AM se shaam 5:30 PM (48 hours per week)."
        ),
        "query": "DFY me leave rules kya hain?",
    },
    {
        "id": "faq_notice_period",
        "category": "DFY HR Manual (Art. 5)",
        "question": "Resignation aur Notice Period ke kya rules hain? Relieving Letter kab milta hai?",
        "answer": (
            "DFY HR Manual Article 5 ke anusar:\n\n"
            "• Resignation par employee ko contract ke anusar notice period (15 days ya 1 month) serve karna hota hai.\n"
            "• Project handover aur departmental **'No Dues Certificate'** clear hone ke baad hi official Relieving Certificate & Experience Letter issue hota hai."
        ),
        "query": "Resignation notice period ka kya rule hai?",
    },
    {
        "id": "faq_insurance",
        "category": "DFY HR Manual (Art. 6)",
        "question": "Employees ko Group Health Insurance me kya medical coverage milta hai?",
        "answer": (
            "DFY HR Manual Article 6 ke anusar:\n\n"
            "• Eligible employees aur project staff ko DFY Group Medical & Accidental Insurance coverage diya jata hai.\n"
            "• Hospitalization ke dauran cashless aur reimbursement claim dono ki suvidha available rehti hai."
        ),
        "query": "Medical insurance policy me kya cover hota hai?",
    },
]


def get_help_guide_data() -> List[Dict[str, Any]]:
    """Loads the step-by-step visual workflow guide data."""
    if not os.path.exists(HELP_GUIDE_PATH):
        return []
    try:
        with open(HELP_GUIDE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Error reading app help guide JSON:", e)
        return []


def get_chatbot_response(user_query: str) -> str:
    """
    Returns friendly, authoritative guidance in Hinglish / English.
    Works 100% offline via local heuristics and policy knowledge.
    """
    res = ai_copilot_service.process_ask_hr_query(user_query)
    ans = res.get("answer", "")
    headline = res.get("headline", "")

    if headline and headline not in ans:
        return f"**{headline}**\n\n{ans}"
    return ans


def help_center_view(page: ft.Page, on_navigate: Optional[Callable] = None, initial_tab: int = 0):
    guides = get_help_guide_data()

    def show_message(text: str, is_success: bool = True):
        try:
            page.open(ft.SnackBar(
                ft.Text(text),
                bgcolor=ft.Colors.GREEN if is_success else ft.Colors.RED
            ))
            page.update()
        except Exception:
            pass

    def trigger_navigate(target: str, **kwargs):
        nav_fn = on_navigate or getattr(page, "on_navigate", None)
        if callable(nav_fn):
            try:
                nav_fn(target, **kwargs)
            except TypeError:
                nav_fn(target)
        else:
            show_message(f"Navigating to {target.title()}...", True)

    # =========================================================================
    # 1. HEADER SECTION
    # =========================================================================
    logo_path = os.path.join(ASSETS_DIR, "dfy_logo112.png")
    if os.path.exists(logo_path):
        header_icon = ft.Image(src=logo_path, width=44, height=44, fit=ft.BoxFit.CONTAIN)
    else:
        header_icon = ft.Icon(ft.Icons.HELP_OUTLINE_ROUNDED, color=PRIMARY_COLOR, size=36)

    header_row = ft.Row([
        ft.Row([
            header_icon,
            ft.Column([
                ft.Row([
                    ft.Text("DFY HR Help Center & Knowledge Hub", size=22, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
                    ui_theme.status_badge("Hinglish & English 🇮🇳"),
                    ui_theme.status_badge("100% Offline 🔒"),
                ], spacing=8, wrap=True),
                ft.Text(
                    "Interactive AI chatbot aur step-by-step workflow guides for non-technical HR managers.",
                    size=12, color=ui_theme.COLOR_TEXT_SECONDARY
                ),
            ], spacing=2),
        ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True)

    # =========================================================================
    # 2. TAB SWITCHER CONTROLS
    # =========================================================================
    state = {
        "active_tab": initial_tab if initial_tab in (0, 1) else 0,
        "search_query": "",
        "filter_category": "all",
    }

    tab1_badge = ft.Container(
        content=ft.Text("Instant AI 💬", size=11, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_PRIMARY_LIGHT),
        bgcolor="#1E3A8A",
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        border_radius=10,
    )

    tab2_badge = ft.Container(
        content=ft.Text(f"{len(guides)} Guides • {len(FAQS_DATA)} FAQs", size=11, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_SUCCESS),
        bgcolor="#064E3B",
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        border_radius=10,
    )

    tab1_header_btn = ft.Container(
        padding=ft.padding.symmetric(horizontal=18, vertical=12),
        border_radius=10,
        bgcolor=ui_theme.COLOR_CARD_BG_HOVER,
        border=ft.Border.all(1.5, ui_theme.COLOR_PRIMARY_LIGHT),
        content=ft.Row([
            ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=20),
            ft.Text("Tab 1: 🤖 DFY AI Chatbot", weight=ft.FontWeight.BOLD, size=13, color=ui_theme.COLOR_TEXT_PRIMARY),
            tab1_badge,
        ], spacing=8, tight=True),
        on_click=lambda e: switch_tab(0),
    )

    tab2_header_btn = ft.Container(
        padding=ft.padding.symmetric(horizontal=18, vertical=12),
        border_radius=10,
        bgcolor=ui_theme.COLOR_CARD_BG,
        border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
        content=ft.Row([
            ft.Icon(ft.Icons.MENU_BOOK_ROUNDED, color=ui_theme.COLOR_TEXT_MUTED, size=20),
            ft.Text("Tab 2: 📚 Workflow Guides & FAQs", weight=ft.FontWeight.BOLD, size=13, color=ui_theme.COLOR_TEXT_SECONDARY),
            tab2_badge,
        ], spacing=8, tight=True),
        on_click=lambda e: switch_tab(1),
    )

    tab_switcher_row = ft.Row([
        tab1_header_btn,
        tab2_header_btn,
    ], spacing=10, wrap=True)

    tab1_container = ft.Container()
    tab2_container = ft.Container()

    def update_tab_header_styles():
        curr = state["active_tab"]
        tab1_header_btn.bgcolor = ui_theme.COLOR_CARD_BG_HOVER if curr == 0 else ui_theme.COLOR_CARD_BG
        tab1_header_btn.border = ft.Border.all(1.5, ui_theme.COLOR_PRIMARY_LIGHT if curr == 0 else ui_theme.COLOR_CARD_BORDER)
        tab1_header_btn.content.controls[0].color = ui_theme.COLOR_PRIMARY_LIGHT if curr == 0 else ui_theme.COLOR_TEXT_MUTED
        tab1_header_btn.content.controls[1].color = ui_theme.COLOR_TEXT_PRIMARY if curr == 0 else ui_theme.COLOR_TEXT_SECONDARY

        tab2_header_btn.bgcolor = ui_theme.COLOR_CARD_BG_HOVER if curr == 1 else ui_theme.COLOR_CARD_BG
        tab2_header_btn.border = ft.Border.all(1.5, ui_theme.COLOR_SUCCESS if curr == 1 else ui_theme.COLOR_CARD_BORDER)
        tab2_header_btn.content.controls[0].color = ui_theme.COLOR_SUCCESS if curr == 1 else ui_theme.COLOR_TEXT_MUTED
        tab2_header_btn.content.controls[1].color = ui_theme.COLOR_TEXT_PRIMARY if curr == 1 else ui_theme.COLOR_TEXT_SECONDARY

        tab1_container.visible = (curr == 0)
        tab2_container.visible = (curr == 1)

    def switch_tab(index: int):
        state["active_tab"] = index
        update_tab_header_styles()
        try:
            page.update()
        except Exception:
            pass

    # =========================================================================
    # 3. TAB 1: INTERACTIVE HINGLISH AI HELP CHATBOT
    # =========================================================================
    chat_history_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def add_chat_bubble(message: str, is_user: bool = False):
        if is_user:
            bubble = ft.Row([
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Text(message, size=13, color=ft.Colors.WHITE),
                    bgcolor=PRIMARY_COLOR,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    border_radius=ft.BorderRadius(top_left=14, top_right=14, bottom_left=14, bottom_right=2),
                    width=460,
                ),
            ], alignment=ft.MainAxisAlignment.END)
        else:
            bubble = ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=20),
                    padding=6,
                    border_radius=20,
                    bgcolor=ft.Colors.with_opacity(0.15, ui_theme.COLOR_PRIMARY_LIGHT),
                ),
                ft.Container(
                    content=ft.Markdown(
                        message,
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    ),
                    bgcolor=ui_theme.COLOR_CARD_BG,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    border_radius=ft.BorderRadius(top_left=2, top_right=14, bottom_left=14, bottom_right=14),
                    border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
                    width=520,
                ),
            ], spacing=8, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)

        chat_history_column.controls.append(bubble)
        try:
            page.update()
        except Exception:
            pass

    def reset_chat_history():
        chat_history_column.controls.clear()
        welcome_msg = (
            "**Namaste! Main DFY HR Assistant hoon.** 🙏\n\n"
            "Aap mujhse software ke kisi bhi feature ya **DFY HR Manual 2025** ki policies ke bare me simple Hindi ya Hinglish me pooch sakte hain.\n\n"
            "Neeche diye gaye kisi bhi question chip par click karein ya apna question type karein:"
        )
        add_chat_bubble(welcome_msg, is_user=False)

    reset_chat_history()

    chat_input = ft.TextField(
        hint_text="Poochhein: 'Offer letter kaise banate hain?', 'DFY me leave rules kya hain?'...",
        expand=True,
        border_radius=10,
        dense=True,
        bgcolor=ui_theme.COLOR_CARD_BG,
        border_color=ui_theme.COLOR_CARD_BORDER,
        focused_border_color=ui_theme.COLOR_PRIMARY_LIGHT,
    )

    def handle_send_message(query_text: str):
        q = (query_text or "").strip()
        if not q:
            return
        add_chat_bubble(q, is_user=True)
        chat_input.value = ""
        try:
            page.update()
        except Exception:
            pass

        # Generate response (offline local heuristics & policy engine)
        response_text = get_chatbot_response(q)
        add_chat_bubble(response_text, is_user=False)

    def on_send_click(e):
        handle_send_message(chat_input.value)

    chat_input.on_submit = on_send_click

    send_btn = ft.IconButton(
        icon=ft.Icons.SEND_ROUNDED,
        icon_color=ft.Colors.WHITE,
        bgcolor=PRIMARY_COLOR,
        on_click=on_send_click,
        tooltip="Send Message (Enter)",
    )

    clear_chat_btn = ft.TextButton(
        content="Clear Chat / New Conversation",
        icon=ft.Icons.REFRESH_ROUNDED,
        on_click=lambda e: reset_chat_history(),
    )

    # Suggestion Chips
    suggestions = [
        "Offer letter kaise banate hain?",
        "Duplicate candidate warning ka kya karein?",
        "Welcome email kab aur kaise bhejein?",
        "DFY me casual leave kitni milti hain?",
        "Office ke working hours kya hain?",
        "Resignation notice period ka kya rule hai?",
        "Medical insurance policy me kya milta hai?",
        "Keka sheet re-upload par duplicate kaise handle karein?",
    ]

    def make_chip_handler(text):
        return lambda e: handle_send_message(text)

    chips_row = ft.Row([
        ft.Chip(
            label=ft.Text(s, size=11),
            on_click=make_chip_handler(s),
        )
        for s in suggestions
    ], wrap=True, spacing=6)

    chatbot_card = ui_theme.modern_card(ft.Column([
        ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=20),
                ft.Text("DFY Hinglish HR Assistant", size=15, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
                ui_theme.status_badge("Active & Ready 🟢"),
            ], spacing=8),
            clear_chat_btn,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
        ft.Divider(height=1, color=ui_theme.COLOR_CARD_BORDER),
        ft.Text("💡 Popular Questions (Click to Ask):", size=11, color=ui_theme.COLOR_TEXT_MUTED, weight=ft.FontWeight.W_600),
        chips_row,
        ft.Container(
            content=chat_history_column,
            height=440,
            border_radius=10,
            padding=12,
            bgcolor=ui_theme.COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
        ),
        ft.Row([chat_input, send_btn], spacing=8),
    ], spacing=10))

    tab1_container.content = ft.Column([
        chatbot_card,
    ], spacing=12)

    # =========================================================================
    # 4. TAB 2: STEP-BY-STEP GUIDES & FAQS (QUESTIONS)
    # =========================================================================
    search_input = ft.TextField(
        hint_text="🔍 Search guides, policies, or questions... (e.g. 'leave', 'offer', 'duplicate', 'keka')",
        expand=True,
        border_radius=10,
        dense=True,
        bgcolor=ui_theme.COLOR_CARD_BG,
        border_color=ui_theme.COLOR_CARD_BORDER,
        focused_border_color=ui_theme.COLOR_SUCCESS,
    )

    guides_list_column = ft.Column(spacing=14)
    faqs_list_column = ft.Column(spacing=10)
    empty_search_message = ft.Container(
        padding=24,
        border_radius=10,
        bgcolor=ui_theme.COLOR_CARD_BG,
        border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
        visible=False,
        content=ft.Column([
            ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, color=ui_theme.COLOR_TEXT_MUTED, size=36),
            ft.Text("No matching guides or questions found.", size=14, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
            ft.Text("Aap search term change karein ya Tab 1 par AI Chatbot se directly poochhein.", size=12, color=ui_theme.COLOR_TEXT_SECONDARY),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
    )

    icon_map = {
        "upload_file_rounded": ft.Icons.UPLOAD_FILE_ROUNDED,
        "mark_email_read_rounded": ft.Icons.MARK_EMAIL_READ_ROUNDED,
        "description_rounded": ft.Icons.DESCRIPTION_ROUNDED,
        "sync_rounded": ft.Icons.SYNC_ROUNDED,
        "menu_book_rounded": ft.Icons.MENU_BOOK_ROUNDED,
    }

    def render_guides_and_faqs():
        guides_list_column.controls.clear()
        faqs_list_column.controls.clear()

        if search_input and search_input.value is not None:
            state["search_query"] = search_input.value

        query = state["search_query"].lower().strip()
        cat = state["filter_category"]

        matched_guides = 0
        matched_faqs = 0

        # 1. Render Workflow Guide Cards
        if cat in ("all", "workflows", "policies"):
            for g in guides:
                title = g.get("title", "")
                tagline = g.get("tagline", "")
                steps = g.get("steps", [])
                pro_tip = g.get("pro_tip", "")
                full_search_text = f"{title} {tagline} {' '.join(steps)} {pro_tip}".lower()

                if query and query not in full_search_text:
                    continue

                matched_guides += 1
                ic = icon_map.get(g.get("icon"), ft.Icons.CHECK_CIRCLE_ROUNDED)
                step_items = [
                    ft.Text(s, size=13, color=ui_theme.COLOR_TEXT_PRIMARY)
                    for s in steps
                ]

                # Direct action button per guide
                gid = g.get("id")
                if gid == "excel_upload":
                    action_btn = ui_theme.primary_button(
                        "🚀 Open Candidate Joining Process",
                        icon=ft.Icons.FILE_UPLOAD_OUTLINED,
                        on_click=lambda e: trigger_navigate("joining"),
                    )
                elif gid == "welcome_emails":
                    action_btn = ui_theme.primary_button(
                        "✉️ Open Selected Candidates",
                        icon=ft.Icons.MARK_EMAIL_READ_ROUNDED,
                        on_click=lambda e: trigger_navigate("joining", filter="Selected"),
                    )
                elif gid == "document_staging":
                    action_btn = ui_theme.primary_button(
                        "📄 Open Document Generator Hub",
                        icon=ft.Icons.RULE_FOLDER_ROUNDED,
                        on_click=lambda e: trigger_navigate("documents"),
                    )
                elif gid == "keka_sync":
                    action_btn = ui_theme.primary_button(
                        "🔄 Open Keka HRMS Sync",
                        icon=ft.Icons.SYNC_ROUNDED,
                        on_click=lambda e: trigger_navigate("keka"),
                    )
                else:
                    action_btn = ui_theme.secondary_button(
                        "🤖 Ask Policy Question in Chatbot",
                        icon=ft.Icons.CHAT_ROUNDED,
                        on_click=lambda e: (switch_tab(0), handle_send_message("DFY leave and working hours policy kya hai?")),
                    )

                card_content = ft.Column([
                    ft.Row([
                        ft.Row([
                            ft.Icon(ic, color=ui_theme.COLOR_PRIMARY_LIGHT, size=24),
                            ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
                        ], spacing=8),
                        ui_theme.status_badge(g.get("badge", "Guide")),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
                    ft.Text(tagline, size=12, color=ui_theme.COLOR_TEXT_MUTED, italic=True),
                    ft.Divider(height=1, color=ui_theme.COLOR_CARD_BORDER),
                    ft.Column(step_items, spacing=6),
                    ft.Container(height=4),
                    ft.Container(
                        bgcolor=ft.Colors.with_opacity(0.12, ui_theme.COLOR_PRIMARY),
                        padding=10,
                        border_radius=8,
                        content=ft.Text(pro_tip, size=11, color=ui_theme.COLOR_PRIMARY_LIGHT, weight=ft.FontWeight.W_500),
                    ),
                    ft.Container(height=4),
                    ft.Row([action_btn], alignment=ft.MainAxisAlignment.END),
                ], spacing=8)

                guides_list_column.controls.append(ui_theme.modern_card(card_content))

        # 2. Render FAQ Cards
        if cat in ("all", "faqs", "policies"):
            for faq in FAQS_DATA:
                q_text = faq.get("question", "")
                a_text = faq.get("answer", "")
                category_name = faq.get("category", "")
                full_faq_search = f"{q_text} {a_text} {category_name}".lower()

                if query and query not in full_faq_search:
                    continue

                matched_faqs += 1

                def make_faq_ask_handler(q_prompt):
                    return lambda e: (switch_tab(0), handle_send_message(q_prompt))

                faq_card = ft.Container(
                    bgcolor=ui_theme.COLOR_CARD_BG,
                    padding=16,
                    border_radius=10,
                    border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
                    content=ft.Column([
                        ft.Row([
                            ft.Row([
                                ft.Icon(ft.Icons.HELP_OUTLINE_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=18),
                                ft.Text(q_text, size=14, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
                            ], spacing=8),
                            ui_theme.status_badge(category_name),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
                        ft.Divider(height=1, color=ui_theme.COLOR_CARD_BORDER),
                        ft.Markdown(
                            a_text,
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        ),
                        ft.Row([
                            ft.TextButton(
                                content="Ask AI Assistant about this 💬",
                                icon=ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED,
                                on_click=make_faq_ask_handler(faq.get("query", q_text)),
                            ),
                        ], alignment=ft.MainAxisAlignment.END),
                    ], spacing=8),
                )
                faqs_list_column.controls.append(faq_card)

        # Show empty state if neither matched
        empty_search_message.visible = (matched_guides == 0 and matched_faqs == 0)

        try:
            page.update()
        except Exception:
            pass

    def on_search_change(e):
        state["search_query"] = search_input.value or ""
        render_guides_and_faqs()

    search_input.on_change = on_search_change

    def set_category(cat_name):
        state["filter_category"] = cat_name
        render_guides_and_faqs()

    category_chips = ft.Row([
        ft.Chip(label=ft.Text("All Topics"), on_click=lambda e: set_category("all")),
        ft.Chip(label=ft.Text("🚀 Workflows"), on_click=lambda e: set_category("workflows")),
        ft.Chip(label=ft.Text("📖 DFY Policy"), on_click=lambda e: set_category("policies")),
        ft.Chip(label=ft.Text("❓ Common FAQs"), on_click=lambda e: set_category("faqs")),
    ], wrap=True, spacing=6)

    tab2_container.content = ft.Column([
        # Search & Filter Toolbar Card
        ui_theme.modern_card(ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.MANAGE_SEARCH_ROUNDED, color=ui_theme.COLOR_SUCCESS, size=22),
                ft.Text("Search Workflow Guides & Frequently Asked Questions", size=15, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
            ], spacing=8),
            search_input,
            category_chips,
        ], spacing=10)),

        empty_search_message,

        ui_theme.section_title(ft.Icons.PLAY_CIRCLE_OUTLINE_ROUNDED, "Step-by-Step System Workflows"),
        guides_list_column,

        ft.Container(height=10),

        ui_theme.section_title(ft.Icons.QUESTION_ANSWER_ROUNDED, "Frequently Asked Questions (HR Operations & Policies)"),
        faqs_list_column,
    ], spacing=12)

    # Initial Render of Tab 2
    render_guides_and_faqs()
    update_tab_header_styles()

    # =========================================================================
    # 5. ASSEMBLE FULL VIEW
    # =========================================================================
    view_column = ft.Column([
        header_row,
        ft.Container(height=6),
        tab_switcher_row,
        ft.Container(height=8),
        tab1_container,
        tab2_container,
        ft.Container(height=20),
    ], scroll=ft.ScrollMode.AUTO, spacing=8, expand=True)

    # Expose controls and methods for unit testing & external invocation
    view_column.chat_history_column = chat_history_column
    view_column.chat_input = chat_input
    view_column.get_chatbot_response = get_chatbot_response
    view_column.switch_tab = switch_tab
    view_column.tab1_container = tab1_container
    view_column.tab2_container = tab2_container
    view_column.search_input = search_input
    view_column.render_guides_and_faqs = render_guides_and_faqs
    view_column.reset_chat_history = reset_chat_history
    view_column.guides_list_column = guides_list_column
    view_column.faqs_list_column = faqs_list_column
    view_column.empty_search_message = empty_search_message

    return view_column
