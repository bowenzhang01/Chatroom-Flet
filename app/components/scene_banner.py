# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · 场景横幅
  监听 scene_changed 事件（由 chat_view 调用 show()），滑入 300ms，
  2.5s 后自动滑出。📍 场景切换 + 场景文本。居中悬浮于聊天区顶部。
"""

import threading

import flet as ft

from app.theme import RADIUS_CARD, TEXT_SM

__all__ = ["SceneBanner"]


class SceneBanner:
    """场景切换横幅（悬浮）。"""

    def __init__(self, page: ft.Page):
        self.page = page
        self._text: ft.Text = None
        self._sub: ft.Text = None
        self._timer: threading.Timer = None
        self._hide_timer: threading.Timer = None
        self.root = self._build()

    def _build(self) -> ft.Control:
        self._text = ft.Text("📍 场景切换", size=TEXT_SM, weight=ft.FontWeight.W_700, color=ft.Colors.PRIMARY)
        self._sub = ft.Text("", size=TEXT_SM, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS)
        card = ft.Container(
            content=ft.Column(
                controls=[self._text, self._sub],
                spacing=2,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=RADIUS_CARD,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            visible=False,
            opacity=0.0,
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            offset=ft.Offset(0, -0.06),
            animate_offset=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color=ft.Colors.with_opacity(0.12, ft.Colors.BLACK),
                offset=ft.Offset(0, 2),
            ),
        )
        # 居中悬浮于顶部
        return ft.Container(
            content=card,
            alignment=ft.Alignment.TOP_CENTER,
            padding=ft.Padding.only(top=8),
            expand=True,
            ignore_interactions=True,
        )

    def show(self, scene: dict):
        if not scene:
            return
        manual = scene.get("manual")
        label = "📍 场景切换" if not manual else "📍 场景已更新"
        if scene.get("is_time_gen"):
            label = "📍 按现实时间生成"
        desc = f"{scene.get('time', '')} · {scene.get('location', '')}".strip(" ·")
        mood = scene.get("mood", "")
        if mood:
            desc = f"{desc}  ·  {mood}" if desc else mood
        self._text.value = label
        self._sub.value = desc or scene.get("scene", "")[:40]
        self.root.content.visible = True
        self.root.content.opacity = 1.0
        self.root.content.offset = ft.Offset(0, 0)
        try:
            self.page.update()
        except Exception:
            pass
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(2.5, self._hide)
        self._timer.daemon = True
        self._timer.start()

    def cancel(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if self._hide_timer:
            self._hide_timer.cancel()
            self._hide_timer = None

    def _hide(self):
        try:
            if self.page is None:
                return
            self.root.content.opacity = 0.0
            self.root.content.offset = ft.Offset(0, -0.06)
            self.page.update()
        except Exception:
            pass
        def _set_invisible():
            try:
                if self.page is None:
                    return
                self.root.content.visible = False
                self.page.update()
            except Exception:
                pass
        t = threading.Timer(0.35, _set_invisible)
        t.daemon = True
        self._hide_timer = t
        t.start()
