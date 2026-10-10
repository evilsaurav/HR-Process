import flet as ft

_shims_applied = False


def apply_flet_compat_shims():
    """
    Centralized compatibility shims for Flet versions.
    Ensures backwards/cross-version compatibility for:
    - Page.open and Page.close
    - ft.border.all
    - ft.ElevatedButton
    - ft.Dropdown (on_change -> on_select)
    """
    global _shims_applied
    if _shims_applied:
        return

    # 1. ft.Page.open and ft.Page.close
    if not hasattr(ft.Page, "open"):
        ft.Page.open = ft.Page.show_dialog
    if not hasattr(ft.Page, "close"):
        ft.Page.close = lambda self, dialog=None: self.pop_dialog()

    # 2. ft.border.all
    if not hasattr(ft.border, "all") and hasattr(ft, "Border") and hasattr(ft.Border, "all"):
        ft.border.all = ft.Border.all

    # 3. ft.ElevatedButton
    if not hasattr(ft, "ElevatedButton") and hasattr(ft, "Button"):
        class CompatibleElevatedButton(ft.Button):
            def __init__(self, text=None, content=None, *args, **kwargs):
                super().__init__(content=content or text, *args, **kwargs)
        ft.ElevatedButton = CompatibleElevatedButton

    # 4. ft.Dropdown on_change -> on_select
    _orig_dropdown_init = ft.Dropdown.__init__

    def _compatible_dropdown_init(self, *args, **kwargs):
        if "on_change" in kwargs and "on_change" not in _orig_dropdown_init.__code__.co_varnames:
            kwargs["on_select"] = kwargs.pop("on_change")
        _orig_dropdown_init(self, *args, **kwargs)

    ft.Dropdown.__init__ = _compatible_dropdown_init

    _shims_applied = True
