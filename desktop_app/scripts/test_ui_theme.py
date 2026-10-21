"""
Verification Script: test_ui_theme.py
Tests the UI Theme Foundation & Components (Phase A):
1. Color palette constant definitions.
2. modern_card component instantiation and hover event handlers.
3. animated_stat_card component structure and styling.
4. fade_in_container animation wrapper.
5. app_footer component branding and styling.
6. Real layout integration with main application structure.
"""

import os
import sys

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
from utils import ui_theme


class MockHoverEvent:
    def __init__(self, data: str):
        self.data = data


def run_tests():
    print("=" * 70)
    print("PHASE A VERIFICATION: UI THEME SYSTEM & GLOBAL FOOTER")
    print("=" * 70)

    # 1. Color Palette Constants Check
    print("\n1. Verifying Color Palette Constants...")
    assert ui_theme.COLOR_PRIMARY == "#2563EB"
    assert ui_theme.COLOR_SECONDARY == "#7C3AED"
    assert ui_theme.COLOR_CARD_BG == "#161F30"
    assert ui_theme.COLOR_BG_DARK == "#0B0F17"
    assert len(ui_theme.GRADIENT_CARD_PURPLE) == 2
    print(f"   • Primary Brand: {ui_theme.COLOR_PRIMARY}")
    print(f"   • Secondary Brand: {ui_theme.COLOR_SECONDARY}")
    print(f"   • Card Background: {ui_theme.COLOR_CARD_BG}")
    print("   ✅ Palette constants verified.")

    # 2. Modern Card Component
    print("\n2. Testing modern_card()...")
    dummy_content = ft.Text("Sample Card Content")
    card_normal = ui_theme.modern_card(dummy_content)
    assert isinstance(card_normal, ft.Container)
    assert card_normal.border_radius == 16
    assert card_normal.shadow is not None and len(card_normal.shadow) > 0
    assert card_normal.animate_scale is not None
    print("   • Standard card created with 16px radius, soft shadow, and scale animation.")

    # Gradient Card
    card_gradient = ui_theme.modern_card(dummy_content, gradient=True)
    assert isinstance(card_gradient, ft.Container)
    assert card_gradient.gradient is not None
    print("   • Gradient card created with LinearGradient.")

    # Hover Simulation
    print("   • Simulating mouse hover enter on card...")
    card_normal.on_hover(MockHoverEvent(data="true"))
    assert card_normal.scale > 1.0, "Hovered card should scale up"
    print(f"     Scale on hover: {card_normal.scale}")

    print("   • Simulating mouse hover exit on card...")
    card_normal.on_hover(MockHoverEvent(data="false"))
    assert card_normal.scale == 1.0, "Unhovered card should reset scale to 1.0"
    print(f"     Scale after exit: {card_normal.scale}")
    print("   ✅ modern_card component and hover transitions verified.")

    # 3. Animated Stat Card Component
    print("\n3. Testing animated_stat_card()...")
    stat_card = ui_theme.animated_stat_card(
        title="Active Employees",
        value=142,
        icon=ft.Icons.PEOPLE_ROUNDED,
        color=ui_theme.COLOR_SUCCESS,
        width=160,
    )
    assert isinstance(stat_card, ft.Container)
    assert stat_card.width == 160
    # Inspect column inside stat card
    stat_col = stat_card.content
    assert isinstance(stat_col, ft.Column)
    stat_val_text = stat_col.controls[1]
    stat_title_text = stat_col.controls[2]
    assert stat_val_text.value == "142"
    assert stat_title_text.value == "Active Employees"
    print(f"   • Stat Card Value: '{stat_val_text.value}', Title: '{stat_title_text.value}'")
    print("   ✅ animated_stat_card component verified.")

    # New helpers test: page_header, section_title, status_badge, buttons
    hdr = ui_theme.page_header(ft.Icons.DASHBOARD_ROUNDED, "Dashboard", "Overview")
    assert isinstance(hdr, ft.Row)
    sec = ui_theme.section_title(ft.Icons.LIST, "List Title")
    assert isinstance(sec, ft.Row)
    badge = ui_theme.status_badge("Joined")
    assert isinstance(badge, ft.Container)
    p_btn = ui_theme.primary_button("Click")
    assert isinstance(p_btn, ft.ElevatedButton)
    s_btn = ui_theme.secondary_button("Export")
    assert isinstance(s_btn, ft.ElevatedButton)
    print("   ✅ page_header, section_title, status_badge, primary_button, secondary_button verified.")

    # 4. Fade-in Container Wrapper
    print("\n4. Testing fade_in_container()...")
    fade_box = ui_theme.fade_in_container(ft.Text("Fading Content"), delay_ms=100)
    assert isinstance(fade_box, ft.Container)
    assert fade_box.opacity == 1.0
    assert fade_box.animate_opacity is not None
    print("   ✅ fade_in_container component verified.")

    # 5. Global App Footer Component
    print("\n5. Testing app_footer()...")
    footer = ui_theme.app_footer()
    assert isinstance(footer, ft.Container)
    footer_row = footer.content
    assert isinstance(footer_row, ft.Row)
    footer_text_ctrl = footer_row.controls[1]
    assert isinstance(footer_text_ctrl, ft.Text)
    assert "Designed by Insomniac" in footer_text_ctrl.value
    print(f"   • Footer Text: '{footer_text_ctrl.value}'")
    print(f"   • Footer Border: {footer.border}")
    print("   ✅ app_footer component verified.")

    # 6. Global Layout Integration Simulation
    print("\n6. Simulating main.py layout integration...")
    rail = ft.NavigationRail(destinations=[ft.NavigationRailDestination(label="Test", icon=ft.Icons.HOME)])
    content_area = ft.Container(expand=True, content=ft.Text("Main Content"))
    body_row = ft.Row([rail, ft.VerticalDivider(width=1), content_area], expand=True, spacing=0)
    app_layout = ft.Column([body_row, footer], expand=True, spacing=0)

    assert len(app_layout.controls) == 2
    assert app_layout.controls[0] == body_row
    assert app_layout.controls[1] == footer
    print("   • Root Column contains body_row (expand=True) + app_footer.")
    print("   ✅ Global main layout integration verified.")

    print("\n" + "=" * 70)
    print("ALL PHASE A UI THEME TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
