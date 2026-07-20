# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · 模式 Chip 组
  [导演][用户][动态场景][随机事件]
  选中=filled，未选=outline。切换后同步 state 标志 + 持久化 profile_config。
"""

import flet as ft

from app.theme import RADIUS_PILL

__all__ = ["ModeChips"]

# (label, attr, config_key, icon)
_MODES = [
    ("导演", "director_mode", "director_mode", ft.Icons.MOVIE),
    ("用户", "user_mode", "user_mode", ft.Icons.PERSON),
    ("动态场景", "dynamic_scene_enabled", "dynamic_scene", ft.Icons.AUTO_AWESOME),
    ("随机事件", "random_event_enabled", "random_event", ft.Icons.CASINO),
]


class ModeChips:
    """模式开关 Chip 组。on_change(mode_key, value) 回调通知外部（如显示输入栏）。"""

    def __init__(self, page: ft.Page, state, on_change=None):
        self.page = page
        self.state = state
        self.on_change = on_change
        self._chips: dict[str, ft.FilterChip] = {}
        self.root = self._build()

    def _build(self) -> ft.Control:
        row = ft.Row(
            controls=[self._make_chip(label, attr, key, icon) for label, attr, key, icon in _MODES],
            spacing=8,
            scroll=ft.ScrollMode.HIDDEN,
        )
        return ft.Container(
            content=row,
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        )

    def _make_chip(self, label, attr, key, icon) -> ft.Chip:
        selected = bool(getattr(self.state, attr, False))
        chip = ft.Chip(
            label=ft.Text(label, size=13, weight=ft.FontWeight.W_500),
            selected=selected,
            leading=ft.Icon(icon, size=16),
            show_checkmark=False,
            on_select=self._make_handler(attr, key),
        )
        self._chips[attr] = chip
        return chip

    def _make_handler(self, attr, key):
        def handler(e: ft.ControlEvent):
            new_val = e.control.selected
            setattr(self.state, attr, new_val)
            # 同步到 profile_config 并持久化
            cfg = self.state._profile_config.setdefault("app", {})
            cfg[key] = new_val
            try:
                self.state.data._save_profile_config()
            except Exception as ex:
                print(f"[mode_chips] 保存 {attr} 失败: {ex}")
            # 用户模式开关：自动加入 / 移除 You
            if attr == "user_mode":
                if new_val:
                    if "You" in self.state.characters and "You" not in self.state.turn_order:
                        self.state.turn_order.append("You")
                        try:
                            self.state.data._save_turn_order()
                        except Exception:
                            pass
                else:
                    if "You" in self.state.turn_order:
                        self.state.turn_order.remove("You")
                        try:
                            self.state.data._save_turn_order()
                        except Exception:
                            pass
            if self.on_change:
                try:
                    self.on_change(attr, new_val)
                except Exception:
                    pass
            self.page.update()
        return handler

    def refresh(self):
        """从 state 同步 chip 选中态。"""
        for label, attr, key, icon in _MODES:
            if attr in self._chips:
                self._chips[attr].selected = bool(getattr(self.state, attr, False))
        try:
            self.page.update()
        except Exception:
            pass
