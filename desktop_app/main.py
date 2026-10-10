from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

import flet as ft
from config import APP_TITLE, PRIMARY_COLOR
from database import db_manager
from pages.joining_process_page import joining_process_view
from pages.settings_page import settings_view


def main(page: ft.Page):
    # Window configuration
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0

    # Initialize SQLite Database
    db_manager.init_db()

    # Content area that switches pages
    content_area = ft.Container(
        expand=True,
        padding=24,
    )

    def navigate_to(index: int):
        rail.selected_index = index
        if index == 0:
            content_area.content = joining_process_view(page)
        elif index == 1:
            content_area.content = settings_view(page)
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        bgcolor=ft.Colors.GREY_950,
        indicator_color=PRIMARY_COLOR,
        leading=ft.Container(
            padding=ft.padding.only(top=16, bottom=16),
            content=ft.Column([
                ft.Icon(ft.Icons.LOCAL_HOSPITAL_ROUNDED, color=PRIMARY_COLOR, size=34),
                ft.Text("DFY HRMS", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
        ),
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.BADGE_OUTLINED,
                selected_icon=ft.Icons.BADGE,
                label="Joining Process",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="Settings",
            ),
        ],
        on_change=lambda e: navigate_to(e.control.selected_index),
    )

    # Initial view
    content_area.content = joining_process_view(page)

    # Main layout: Sidebar NavigationRail on left, content area on right
    page.add(
        ft.Row([
            rail,
            ft.VerticalDivider(width=1, color=ft.Colors.GREY_800),
            content_area,
        ], expand=True, spacing=0)
    )


if __name__ == "__main__":
    ft.app(target=main)
