# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · TransportBar 工具条
  轮流 ▾ Dropdown + 速度 ━●━━ Slider + ▶/⏸/⏹ 三按钮 + 💾(暂停时显示)
  绑定 state.loop.start / pause / resume / stop / set_speed / set_mode
"""

import flet as ft

from app.theme import COLORS, RADIUS_PILL

__all__ = ["TransportBar"]

_MODES = [
    ("轮流", "round"),
    ("随机", "random"),
    ("动态", "dynamic"),
]


class TransportBar:
    """对话控制工具条。on_action(action) 回调通知外部（如弹停止确认）。"""

    def __init__(self, page: ft.Page, state, on_action=None):
        self.page = page
        self.state = state
        self.on_action = on_action  # action: "start"|"pause"|"resume"|"stop"|"save"
        self._mode_dd: ft.Dropdown = None
        self._speed_slider: ft.Slider = None
        self._play_btn: ft.IconButton = None
        self._stop_btn: ft.IconButton = None
        self._save_btn: ft.IconButton = None
        self.root = self._build()

    def _build(self) -> ft.Control:
        self._mode_dd = ft.Dropdown(
            value=self.state.mode if self.state.mode in ("round", "random", "dynamic") else "round",
            options=[ft.dropdown.Option(v, text=l) for l, v in _MODES],
            dense=True,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            width=110,
            on_select=self._on_mode_change,
        )

        self._play_btn = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            selected_icon=ft.Icons.PAUSE,
            selected=False,
            icon_size=22,
            tooltip="开始 / 暂停",
            on_click=self._on_play_click,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.PRIMARY,
                icon_color=ft.Colors.ON_PRIMARY,
            ),
        )
        self._stop_btn = ft.IconButton(
            icon=ft.Icons.STOP_CIRCLE_OUTLINED,
            icon_size=22,
            tooltip="停止",
            on_click=self._on_stop_click,
        )
        self._save_btn = ft.IconButton(
            icon=ft.Icons.SAVE_OUTLINED,
            icon_size=20,
            tooltip="保存当前对话",
            on_click=self._on_save_click,
            visible=False,
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    self._mode_dd,
                    ft.Container(expand=True),
                    self._play_btn,
                    self._stop_btn,
                    self._save_btn,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        )

    # ═══ 事件 ═══
    def _on_mode_change(self, e):
        v = e.control.value
        if v:
            self.state.loop.set_mode(v)

    def _on_play_click(self, e):
        loop = self.state.loop
        if not loop.running:
            self._emit("start")
        elif loop.paused:
            self._emit("resume")
        else:
            self._emit("pause")

    def _on_stop_click(self, e):
        self._emit("stop")

    def _on_save_click(self, e):
        self._emit("save")

    def _emit(self, action):
        if self.on_action:
            try:
                self.on_action(action)
            except Exception:
                pass

    # ═══ 状态同步（由 EventBus 事件驱动）═══
    def set_running(self, running: bool, paused: bool):
        """更新播放按钮 + 保存按钮可见性。"""
        if running:
            self._play_btn.selected = not paused
            self._play_btn.icon = ft.Icons.PLAY_ARROW if paused else ft.Icons.PAUSE
            self._stop_btn.disabled = False
            self._save_btn.visible = paused
        else:
            self._play_btn.selected = False
            self._play_btn.icon = ft.Icons.PLAY_ARROW
            self._stop_btn.disabled = True
            self._save_btn.visible = False
        try:
            self.page.update()
        except Exception:
            pass

    def refresh(self):
        self._mode_dd.value = self.state.mode if self.state.mode in ("round", "random", "dynamic") else "round"
        self.set_running(self.state.running, self.state.paused)
