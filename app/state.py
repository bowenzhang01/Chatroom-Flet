# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · UI 反应式状态
  持有跨视图共享的 UI 状态：当前路由 / 主题模式 / 对话框引用等。
  与 core.AppState（业务层）分离：UIState 只管"怎么显示"，AppState 管"是什么"。
"""

import flet as ft

from app.theme import THEME_MODES, set_color_theme

__all__ = ["UIState"]


class UIState:
    """UI 层共享状态。"""

    # ── 路由 ──
    route: str = "/chat"

    # ── 主题模式 ──
    theme_mode_key: str = "system"  # light | dark | system

    # ── 色彩主题 ──
    color_theme_key: str = "aurora"  # aurora | dusk | ocean | star

    # ── 响应式断点 ──
    def is_desktop(self, page: ft.Page) -> bool:
        return page.width >= 900

    # ── 主题模式 → ft.ThemeMode ──
    def theme_mode(self) -> ft.ThemeMode:
        return THEME_MODES.get(self.theme_mode_key, ft.ThemeMode.SYSTEM)

    # ── 持久化 ──
    def load_theme_mode(self):
        import config
        ui = config.app_config.setdefault("ui", {})
        self.theme_mode_key = ui.get("theme_mode", "system")
        self.color_theme_key = ui.get("color_theme", "aurora")
        set_color_theme(self.color_theme_key)

    def save_theme_mode(self):
        import config
        from utils import save_json
        ui = config.app_config.setdefault("ui", {})
        ui["theme_mode"] = self.theme_mode_key
        save_json(config.BASE_DIR / "config.json", config.app_config)

    def save_color_theme(self):
        import config
        from utils import save_json
        ui = config.app_config.setdefault("ui", {})
        ui["color_theme"] = self.color_theme_key
        set_color_theme(self.color_theme_key)
        save_json(config.BASE_DIR / "config.json", config.app_config)
