"""
Page: help_center_page.py
Purpose: Dedicated Help Center & Interactive Hinglish AI Chatbot for Doctors For You HRMS.
Designed specifically for non-technical HR managers and field coordinators.
Features:
- Visual step-by-step workflow guide cards (Upload, Welcome Email, Document Staging, Keka Sync, DFY Policy).
- Interactive Hinglish AI Help Chatbot with quick suggestion chips.
- 100% Guaranteed Offline execution using local knowledge guides & DFY policy engine.
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


def help_center_view(page: ft.Page, on_navigate: Optional[Callable] = None):
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
                    ft.Text("DFY HR Help Center & User Guide", size=24, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
                    ui_theme.status_badge("Hinglish & English Supported 🇮🇳"),
                ], spacing=8),
                ft.Text(
                    "Non-technical HR users ke liye aasan step-by-step guide aur interactive AI assistant.",
                    size=13, color=ui_theme.COLOR_TEXT_SECONDARY
                ),
            ], spacing=2, expand=True),
        ], spacing=14, expand=True),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # =========================================================================
    # 2. STEP-BY-STEP VISUAL WORKFLOW CARDS
    # =========================================================================
    guide_cards = []
    icon_map = {
        "upload_file_rounded": ft.Icons.UPLOAD_FILE_ROUNDED,
        "mark_email_read_rounded": ft.Icons.MARK_EMAIL_READ_ROUNDED,
        "description_rounded": ft.Icons.DESCRIPTION_ROUNDED,
        "sync_rounded": ft.Icons.SYNC_ROUNDED,
        "menu_book_rounded": ft.Icons.MENU_BOOK_ROUNDED,
    }

    for g in guides:
        ic = icon_map.get(g.get("icon"), ft.Icons.CHECK_CIRCLE_ROUNDED)
        step_items = [
            ft.Text(s, size=13, color=ui_theme.COLOR_TEXT_PRIMARY)
            for s in g.get("steps", [])
        ]

        card_content = ft.Column([
            ft.Row([
                ft.Icon(ic, color=ui_theme.COLOR_PRIMARY_LIGHT, size=24),
                ft.Text(g.get("title", ""), size=15, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
                ft.Container(expand=True),
                ui_theme.status_badge(g.get("badge", "Guide")),
            ], spacing=8),
            ft.Text(g.get("tagline", ""), size=12, color=ui_theme.COLOR_TEXT_MUTED, italic=True),
            ft.Divider(height=1, color=ui_theme.COLOR_CARD_BORDER),
            ft.Column(step_items, spacing=6),
            ft.Container(height=4),
            ft.Container(
                bgcolor=ft.Colors.with_opacity(0.12, ui_theme.COLOR_PRIMARY),
                padding=8,
                border_radius=8,
                content=ft.Text(g.get("pro_tip", ""), size=11, color=ui_theme.COLOR_PRIMARY_LIGHT, weight=ft.FontWeight.W_500),
            ),
        ], spacing=8)

        guide_cards.append(
            ui_theme.modern_card(card_content)
        )

    guide_column = ft.Column(guide_cards, spacing=14)

    # =========================================================================
    # 3. INTERACTIVE HINGLISH AI HELP CHATBOT
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
                    width=420,
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
                    width=480,
                ),
            ], spacing=8, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)

        chat_history_column.controls.append(bubble)
        try:
            page.update()
        except Exception:
            pass

    # Initial Welcome message
    welcome_msg = (
        "**Namaste! Main DFY HR Assistant hoon.** 🙏\n\n"
        "Aap mujhse software ke kisi bhi feature ya **DFY HR Manual 2025** ki policies ke bare me simple Hindi ya Hinglish me pooch sakte hain.\n"
        "Neeche diye gaye kisi bhi question par click karein ya apna question type karein:"
    )
    add_chat_bubble(welcome_msg, is_user=False)

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

        # Generate response (offline or online)
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
        tooltip="Send Message",
    )

    # Suggestion Chips
    suggestions = [
        "Offer letter kaise banate hain?",
        "Duplicate candidate warning ka kya karein?",
        "DFY me casual leave kitni milti hain?",
        "Office ke working hours kya hain?",
        "Resignation notice period ka kya rule hai?",
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
            ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=20),
            ft.Text("DFY Hinglish HR Assistant (100% Offline Capable)", size=15, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
            ft.Container(expand=True),
            ui_theme.status_badge("Instant AI Help 💬"),
        ], spacing=8),
        ft.Divider(height=1, color=ui_theme.COLOR_CARD_BORDER),
        chips_row,
        ft.Container(
            content=chat_history_column,
            height=320,
            border_radius=8,
            padding=10,
            bgcolor=ui_theme.COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
        ),
        ft.Row([chat_input, send_btn], spacing=8),
    ], spacing=10))

    # =========================================================================
    # 4. ASSEMBLE FULL VIEW
    # =========================================================================
    view_column = ft.Column([
        header_row,
        ft.Container(height=8),
        ui_theme.section_title(ft.Icons.CHAT_ROUNDED, "🤖 Ask DFY HR Assistant (Chatbot)"),
        chatbot_card,
        ft.Container(height=10),
        ui_theme.section_title(ft.Icons.LOCAL_LIBRARY_ROUNDED, "📖 Step-by-Step Workflow Guide (Non-Technical)"),
        guide_column,
        ft.Container(height=20),
    ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True)

    view_column.chat_history_column = chat_history_column
    view_column.chat_input = chat_input
    view_column.get_chatbot_response = get_chatbot_response

    return view_column
