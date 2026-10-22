from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

import os
import threading
import time
import flet as ft
from config import APP_TITLE, PRIMARY_COLOR, ASSETS_DIR
from database import db_manager
from services import email_scheduler_service
from pages.dashboard_page import dashboard_view
from pages.joining_process_page import joining_process_view
from pages.keka_sync_page import keka_sync_view
from pages.document_generation_page import document_generation_view
from pages.settings_page import settings_view
from pages.help_center_page import help_center_view
from utils.ui_theme import app_footer

_scheduler_started = False


def _run_email_scheduler_loop():
    while True:
        try:
            email_scheduler_service.process_due_scheduled_emails()
        except Exception:
            pass
        time.sleep(30)


def start_scheduler_thread():
    global _scheduler_started
    if not _scheduler_started:
        _scheduler_started = True
        threading.Thread(target=_run_email_scheduler_loop, daemon=True).start()


def main(page: ft.Page):
    # Window configuration
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0

    logo_path = os.path.join(ASSETS_DIR, "dfy_logo112.png")
    if os.path.exists(logo_path):
        try:
            if hasattr(page, "window") and hasattr(page.window, "icon"):
                page.window.icon = logo_path
        except Exception:
            pass

    # Initialize SQLite Database
    db_manager.init_db()
    start_scheduler_thread()

    # Content area that switches pages
    content_area = ft.Container(
        expand=True,
        padding=24,
    )

    def navigate_to(index_or_target, **kwargs):
        if isinstance(index_or_target, str):
            mapping = {
                "dashboard": 0,
                "joining": 1,
                "joining_process": 1,
                "keka": 2,
                "keka_sync": 2,
                "documents": 3,
                "document_generation": 3,
                "settings": 4,
                "help": 5,
                "help_center": 5,
            }
            index = mapping.get(index_or_target.lower(), 0)
        else:
            index = int(index_or_target)

        rail.selected_index = index
        if index == 0:
            content_area.content = dashboard_view(page, on_navigate=navigate_to)
        elif index == 1:
            initial_filter = kwargs.get("filter") or kwargs.get("initial_filter")
            content_area.content = joining_process_view(page, initial_filter=initial_filter)
        elif index == 2:
            content_area.content = keka_sync_view(page)
        elif index == 3:
            initial_tab = kwargs.get("tab") if "tab" in kwargs else kwargs.get("initial_tab", 0)
            content_area.content = document_generation_view(page, initial_tab=int(initial_tab or 0))
        elif index == 4:
            content_area.content = settings_view(page)
        elif index == 5:
            content_area.content = help_center_view(page, on_navigate=navigate_to)
        page.update()

    page.on_navigate = navigate_to
    if hasattr(page, "session"):
        try:
            page.session.set("navigate_to", navigate_to)
        except Exception:
            pass

    if os.path.exists(logo_path):
        rail_logo = ft.Image(src=logo_path, width=44, height=44, fit=ft.BoxFit.CONTAIN)
    else:
        rail_logo = ft.Icon(ft.Icons.LOCAL_HOSPITAL_ROUNDED, color=PRIMARY_COLOR, size=34)

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        bgcolor=ft.Colors.GREY_900,
        indicator_color=PRIMARY_COLOR,
        leading=ft.Container(
            padding=ft.padding.only(top=16, bottom=16),
            content=ft.Column([
                rail_logo,
                ft.Text("DFY HRMS", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
        ),
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD_OUTLINED,
                selected_icon=ft.Icons.DASHBOARD,
                label="Dashboard",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.BADGE_OUTLINED,
                selected_icon=ft.Icons.BADGE,
                label="Joining Process",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SYNC_ROUNDED,
                selected_icon=ft.Icons.SYNC,
                label="Keka Sync",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DESCRIPTION_OUTLINED,
                selected_icon=ft.Icons.DESCRIPTION,
                label="Document Generator",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="Settings",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.HELP_OUTLINE_ROUNDED,
                selected_icon=ft.Icons.HELP_ROUNDED,
                label="Help Center",
            ),
        ],
        on_change=lambda e: navigate_to(e.control.selected_index),
    )

    # Initial view (Executive Dashboard)
    content_area.content = dashboard_view(page, on_navigate=navigate_to)

    # Main layout: Sidebar NavigationRail on left, content area on right, global footer at bottom
    body_row = ft.Row([
        rail,
        ft.VerticalDivider(width=1, color=ft.Colors.GREY_800),
        content_area,
    ], expand=True, spacing=0)

    page.add(
        ft.Column([
            body_row,
            app_footer(),
        ], expand=True, spacing=0)
    )


if __name__ == "__main__":
    import sys
    view_mode = ft.AppView.WEB_BROWSER if "--web" in sys.argv else ft.AppView.FLET_APP
    if hasattr(ft, "run"):
        ft.run(main, view=view_mode)
    else:
        ft.app(target=main, view=view_mode)
