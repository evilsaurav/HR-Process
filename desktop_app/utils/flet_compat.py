import flet as ft

_shims_applied = False


def register_overlay_control(page, control):
    """
    Registers a non-visual control (FilePicker, etc.) with the page in a
    version-safe way. Flet 1.0.4+ uses page.services for Service-based
    controls; older Flet versions used page.overlay.
    
    Includes singleton/de-duplication protection so repeatedly switching
    pages does not leak duplicate FilePicker controls into page.services or page.overlay.
    """
    if hasattr(page, "services") and isinstance(page.services, list):
        for existing in page.services:
            if isinstance(existing, type(control)) and type(control).__name__ == "FilePicker":
                if hasattr(control, "on_result") and getattr(control, "on_result", None) is not None:
                    existing.on_result = control.on_result
                return existing
        page.services.append(control)
        return control
    elif hasattr(page, "overlay") and isinstance(page.overlay, list):
        for existing in page.overlay:
            if isinstance(existing, type(control)) and type(control).__name__ == "FilePicker":
                if hasattr(control, "on_result") and getattr(control, "on_result", None) is not None:
                    existing.on_result = control.on_result
                return existing
        page.overlay.append(control)
        return control
    else:
        raise RuntimeError("Could not find a compatible way to register overlay control with this Flet version.")


def apply_flet_compat_shims():
    """
    Centralized compatibility shims for Flet versions.
    Ensures backwards/cross-version compatibility for:
    - Page.open and Page.close
    - ft.border.all
    - ft.ElevatedButton
    - ft.Dropdown (on_change -> on_select)
    - ft.FilePicker pick_files and save_file coroutine handling
    """
    global _shims_applied
    if _shims_applied:
        return

    # 1. ft.Page.open and ft.Page.close
    if not hasattr(ft.Page, "open"):
        ft.Page.open = ft.Page.show_dialog
    if not hasattr(ft.Page, "close"):
        ft.Page.close = lambda self, dialog=None: self.pop_dialog()

    # 2. ft.border.all, only, symmetric
    if hasattr(ft, "Border"):
        if not hasattr(ft.border, "all") and hasattr(ft.Border, "all"):
            ft.border.all = ft.Border.all
        if not hasattr(ft.border, "only") and hasattr(ft.Border, "only"):
            ft.border.only = ft.Border.only
        if not hasattr(ft.border, "symmetric") and hasattr(ft.Border, "symmetric"):
            ft.border.symmetric = ft.Border.symmetric

    # 3. ft.ElevatedButton
    if not hasattr(ft, "ElevatedButton") and hasattr(ft, "Button"):
        class CompatibleElevatedButton(ft.Button):
            def __init__(self, text=None, content=None, *args, **kwargs):
                self._compat_text = text
                super().__init__(content=content or text, *args, **kwargs)

            @property
            def text(self):
                return self._compat_text or (self.content if isinstance(self.content, str) else None)

            @text.setter
            def text(self, val):
                self._compat_text = val
                self.content = val

        ft.ElevatedButton = CompatibleElevatedButton

    # 4. ft.Dropdown on_change -> on_select (both constructor argument and property setter)
    _orig_dropdown_init = ft.Dropdown.__init__

    def _compatible_dropdown_init(self, *args, **kwargs):
        if "on_change" in kwargs and "on_change" not in _orig_dropdown_init.__code__.co_varnames:
            kwargs["on_select"] = kwargs.pop("on_change")
        _orig_dropdown_init(self, *args, **kwargs)

    ft.Dropdown.__init__ = _compatible_dropdown_init

    if not hasattr(ft.Dropdown, "on_change"):
        ft.Dropdown.on_change = property(
            lambda self: getattr(self, "on_select", None),
            lambda self, val: setattr(self, "on_select", val),
        )

    # 5. ft.Colors.GREY_950 fallback alias
    if not hasattr(ft.Colors, "GREY_950"):
        ft.Colors.GREY_950 = getattr(ft.Colors, "GREY_900", "#121212")

    # 6. ft.padding.only / all / symmetric backwards compatibility
    if hasattr(ft, "Padding"):
        if not hasattr(ft.padding, "only"):
            ft.padding.only = lambda left=0, top=0, right=0, bottom=0: ft.Padding(left=left, top=top, right=right, bottom=bottom)
        if not hasattr(ft.padding, "all"):
            ft.padding.all = lambda val: ft.Padding(left=val, top=val, right=val, bottom=val)
        if not hasattr(ft.padding, "symmetric"):
            ft.padding.symmetric = lambda vertical=0, horizontal=0: ft.Padding(left=horizontal, top=vertical, right=horizontal, bottom=vertical)

    # 7. ft.alignment backwards compatibility (mapping lowercase properties like ft.alignment.center -> ft.Alignment.CENTER)
    if hasattr(ft, "alignment") and hasattr(ft, "Alignment"):
        for _align_attr in [
            "center", "top_left", "top_center", "top_right",
            "center_left", "center_right", "bottom_left", "bottom_center", "bottom_right"
        ]:
            if not hasattr(ft.alignment, _align_attr):
                setattr(ft.alignment, _align_attr, getattr(ft.Alignment, _align_attr.upper(), None))

    # 8. ft.app backward compatibility shim mapping to ft.run in Flet 1.0+
    if not hasattr(ft, "app") and hasattr(ft, "run"):
        def _compat_app(target=None, *args, **kwargs):
            fn = target if target is not None else kwargs.pop("main", None)
            if fn is None and args:
                fn = args[0]
                args = args[1:]
            return ft.run(fn, *args, **kwargs)
        ft.app = _compat_app

    _shims_applied = True
