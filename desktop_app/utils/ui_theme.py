"""
Theme & Visual Design System: ui_theme.py
Purpose: Centralized modern visual foundations for DFY HRMS Desktop.
Provides modern-depth illusions (shadows, gradients, glassmorphism),
smooth hover animations, consistent typography colors, and global footer.

=============================================================================
FLET 1.0.4 UI API REFERENCE FINDINGS:
=============================================================================
1. Shadows:
   - `ft.BoxShadow` exists; `ft.Shadow` does not exist in Flet 1.0.4.
   - Parameters: `blur_radius` (float), `spread_radius` (float),
     `color` (ColorValue e.g. ft.Colors.BLACK_54 or ft.Colors.with_opacity(0.4, ft.Colors.BLACK)),
     `offset=ft.Offset(x, y)`.
   - Used inside `ft.Container(shadow=[ft.BoxShadow(...)])`.

2. Gradients:
   - `ft.LinearGradient` exists.
   - Parameters: `begin=ft.Alignment.TOP_LEFT`, `end=ft.Alignment.BOTTOM_RIGHT`,
     `colors=['#hex1', '#hex2']`, optional `stops=[0.0, 1.0]`.
   - Used inside `ft.Container(gradient=ft.LinearGradient(...))`.

3. Container Animations:
   - `animate` parameter accepts `ft.Animation(duration=ms, curve=ft.AnimationCurve.XXX)`.
   - `animate_scale`: animates scale transforms smoothly.
   - `animate_opacity`: animates opacity changes smoothly.
   - `animate_offset`: animates translation displacement smoothly.
   - `animate_size` & `animate_position`: animates layout dimensions and positioning.
   - Supported easing curves include `ft.AnimationCurve.EASE_OUT`, `DECELERATE`, `FAST_OUT_SLOW_IN`.

4. Hover Detection:
   - `ft.Container` has native `on_hover` event handler.
   - Inside `on_hover(e)`, `e.data == "true"` indicates mouse enter, `"false"` indicates mouse leave.

5. Global Footer:
   - Minimalist bottom bar with 'Designed by Insomniac' label and subtle accent.
=============================================================================
"""

from typing import Optional, Union
import flet as ft
from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

# =============================================================================
# COLOR PALETTE CONSTANTS
# =============================================================================

# Brand Primary & Secondary
COLOR_PRIMARY = "#2563EB"          # Vibrant Electric Blue
COLOR_PRIMARY_LIGHT = "#3B82F6"    # Lighter Blue highlight
COLOR_PRIMARY_DARK = "#1D4ED8"     # Deep Royal Blue
COLOR_SECONDARY = "#7C3AED"        # Royal Purple / Violet Accent
COLOR_SECONDARY_LIGHT = "#8B5CF6"  # Violet highlight

# Semantic Status Colors
COLOR_SUCCESS = "#10B981"          # Emerald Green
COLOR_SUCCESS_BG = "#064E3B"       # Dark Emerald surface
COLOR_WARNING = "#F59E0B"          # Amber / Orange
COLOR_WARNING_BG = "#78350F"       # Dark Amber surface
COLOR_ERROR = "#EF4444"            # Rose / Red
COLOR_ERROR_BG = "#7F1D1D"         # Dark Rose surface
COLOR_INFO = "#06B6D4"             # Sky / Cyan
COLOR_INFO_BG = "#164E63"          # Dark Cyan surface

# Backgrounds & Elevated Surfaces (Dark Mode Depth)
COLOR_BG_DARK = "#0B0F17"           # Root canvas background (deep midnight)
COLOR_SURFACE_DARK = "#111827"      # Navigation Rail / App shell surface
COLOR_CARD_BG = "#161F30"           # Elevated Card surface (Slate 900 tint)
COLOR_CARD_BG_HOVER = "#1E293B"     # Hover state elevated surface
COLOR_CARD_BORDER = "#1E293B"       # Subtle card border line
COLOR_CARD_BORDER_HOVER = "#3B82F6" # Glowing border on hover

# Gradients
GRADIENT_CARD_PURPLE = ["#1E1B4B", "#0F172A"]  # Indigo to Midnight Slate
GRADIENT_PRIMARY = ["#2563EB", "#7C3AED"]      # Electric Blue to Violet
GRADIENT_STAT_GLOW = ["#1E293B", "#0F172A"]    # Muted dual-tone slate
GRADIENT_HEADER = ["#1E293B", "#111827"]       # Subtitle header gradient

# Typography Colors
COLOR_TEXT_PRIMARY = "#F8FAFC"      # Pure high-contrast white/slate
COLOR_TEXT_SECONDARY = "#94A3B8"    # Medium contrast body text
COLOR_TEXT_MUTED = "#64748B"        # Subtle secondary text / captions
COLOR_TEXT_HINT = "#475569"         # Muted labels / borders


# =============================================================================
# REUSABLE MODERN COMPONENTS
# =============================================================================

def modern_card(
    content: ft.Control,
    gradient: bool = False,
    on_click=None,
    padding: int = 20,
    border_radius: int = 16,
    expand: Optional[Union[bool, int]] = None,
    width=None,
    height=None,
) -> ft.Container:
    """
    Creates an elevated, modern-depth card with rounded corners,
    subtle outer shadow, and smooth hover-lift animation.
    """
    initial_shadow = [
        ft.BoxShadow(
            blur_radius=12,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
            offset=ft.Offset(0, 4),
        )
    ]

    hover_shadow = [
        ft.BoxShadow(
            blur_radius=20,
            spread_radius=1,
            color=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            offset=ft.Offset(0, 8),
        )
    ]

    card_bg = None if gradient else COLOR_CARD_BG
    card_gradient = (
        ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=GRADIENT_CARD_PURPLE,
        )
        if gradient
        else None
    )

    card_container = ft.Container(
        content=content,
        padding=padding,
        border_radius=border_radius,
        bgcolor=card_bg,
        gradient=card_gradient,
        border=ft.Border.all(1, COLOR_CARD_BORDER),
        shadow=initial_shadow,
        scale=1.0,
        expand=expand,
        width=width,
        height=height,
        on_click=on_click,
        animate_scale=ft.Animation(duration=180, curve=ft.AnimationCurve.EASE_OUT),
        animate=ft.Animation(duration=180, curve=ft.AnimationCurve.EASE_OUT),
    )

    def on_card_hover(e):
        is_hovered = e.data == "true"
        if is_hovered:
            card_container.scale = 1.012
            card_container.shadow = hover_shadow
            card_container.border = ft.Border.all(
                1, COLOR_PRIMARY_LIGHT if on_click else "#334155"
            )
        else:
            card_container.scale = 1.0
            card_container.shadow = initial_shadow
            card_container.border = ft.Border.all(1, COLOR_CARD_BORDER)
        try:
            card_container.update()
        except Exception:
            pass

    card_container.on_hover = on_card_hover
    return card_container


def animated_stat_card(
    title: str,
    value: int | str,
    icon,
    color: str = COLOR_PRIMARY,
    width: int = 150,
) -> ft.Container:
    """
    Creates an interactive executive stat card with an icon badge,
    bold numeric value, and smooth hover elevation.
    """
    icon_badge = ft.Container(
        content=ft.Icon(icon, color=color, size=20),
        padding=6,
        border_radius=8,
        bgcolor=ft.Colors.with_opacity(0.15, color),
    )

    inner_content = ft.Column(
        [
            ft.Row([icon_badge]),
            ft.Text(str(value), size=24, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
            ft.Text(title, size=12, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500),
        ],
        spacing=4,
    )

    return modern_card(
        content=inner_content,
        padding=16,
        border_radius=14,
        width=width,
    )


def fade_in_container(
    content: ft.Control,
    delay_ms: int = 0,
    expand: Optional[Union[bool, int]] = None,
) -> ft.Container:
    """
    Generic wrapper providing smooth entrance transition for UI views.
    """
    return ft.Container(
        content=content,
        opacity=1.0,
        animate_opacity=ft.Animation(duration=350, curve=ft.AnimationCurve.EASE_OUT),
        expand=expand,
    )


def page_header(icon, title: str, subtitle: str) -> ft.Row:
    """
    Consistent, modern page header across all application views.
    Features an accented icon badge, bold title, and clean subtitle.
    """
    icon_badge = ft.Container(
        content=ft.Icon(icon, color=COLOR_PRIMARY_LIGHT, size=28),
        padding=10,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.12, COLOR_PRIMARY),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.2, COLOR_PRIMARY_LIGHT)),
    )

    return ft.Row(
        [
            icon_badge,
            ft.Column(
                [
                    ft.Text(title, size=26, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                    ft.Text(subtitle, size=13, color=COLOR_TEXT_SECONDARY),
                ],
                spacing=2,
                expand=True,
            ),
        ],
        spacing=14,
    )


def section_title(icon, text: str, action: ft.Control = None) -> ft.Row:
    """
    Consistent section title with primary accent icon and optional right-aligned action.
    """
    left = ft.Row(
        [
            ft.Icon(icon, color=COLOR_PRIMARY_LIGHT, size=20),
            ft.Text(text, size=17, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
        ],
        spacing=8,
    )
    if action:
        return ft.Row([left, ft.Container(expand=True), action], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    return left


def status_badge(text: str) -> ft.Container:
    """
    Modern pill/chip badge for pipeline statuses, document status, and lifecycle alerts.
    """
    t = str(text or "").strip()
    t_lower = t.lower()

    if "joined" in t_lower or "issued" in t_lower or "success" in t_lower or t_lower in ["yes", "active", "verified"]:
        fg, bg, border = COLOR_SUCCESS, "#064E3B", "#059669"
    elif "offer" in t_lower:
        fg, bg, border = COLOR_PRIMARY_LIGHT, "#1E3A8A", "#2563EB"
    elif "interview" in t_lower or "due soon" in t_lower:
        fg, bg, border = COLOR_WARNING, "#78350F", "#D97706"
    elif "shortlisted" in t_lower:
        fg, bg, border = COLOR_INFO, "#164E63", "#0891B2"
    elif "applied" in t_lower:
        fg, bg, border = COLOR_SECONDARY_LIGHT, "#4C1D95", "#7C3AED"
    elif "rejected" in t_lower or "overdue" in t_lower or "action needed" in t_lower or "failed" in t_lower:
        fg, bg, border = COLOR_ERROR, "#7F1D1D", "#DC2626"
    elif "pending" in t_lower or "warning" in t_lower:
        fg, bg, border = "#FDE047", "#713F12", "#CA8A04"
    else:
        fg, bg, border = COLOR_TEXT_SECONDARY, "#1E293B", "#334155"

    return ft.Container(
        content=ft.Text(t, size=11, weight=ft.FontWeight.BOLD, color=fg),
        bgcolor=bg,
        border=ft.Border.all(1, border),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=6,
    )


def primary_button(
    text: str,
    icon=None,
    on_click=None,
    disabled: bool = False,
    bgcolor: str = COLOR_PRIMARY,
) -> ft.ElevatedButton:
    """Consistent primary action button."""
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        bgcolor=bgcolor,
        color=ft.Colors.WHITE,
        disabled=disabled,
        on_click=on_click,
    )


def secondary_button(
    text: str,
    icon=None,
    on_click=None,
    disabled: bool = False,
) -> ft.ElevatedButton:
    """Consistent secondary / utility action button."""
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        bgcolor=COLOR_CARD_BG_HOVER,
        color=COLOR_TEXT_PRIMARY,
        disabled=disabled,
        on_click=on_click,
    )


def app_footer() -> ft.Container:
    """
    Global application footer:
    'Designed by Insomniac'
    Subtle, centered, modern minimal branding with a clean top border.
    """
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, size=13, color=COLOR_TEXT_MUTED),
                ft.Text(
                    "Designed by Insomniac",
                    size=11,
                    weight=ft.FontWeight.W_500,
                    color=COLOR_TEXT_MUTED,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=6,
        ),
        padding=ft.padding.symmetric(vertical=9),
        border=ft.Border.only(
            top=ft.BorderSide(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE))
        ),
        bgcolor=COLOR_SURFACE_DARK,
    )
