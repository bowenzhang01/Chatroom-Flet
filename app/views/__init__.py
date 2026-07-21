# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · 视图基类。

所有视图继承 ViewBase，持有 page / state / ui / router 引用。
子类实现 build() 返回根控件，on_enter() 在路由进入时调用。
"""

import time
import flet as ft

from app.theme import TEXT_ML, TEXT_SM

__all__ = ["ViewBase"]


class ViewBase:
    """视图基类（非 ft.Control，返回 ft.Control 给 router 装填）。"""

    def __init__(self, page: ft.Page, app_state, ui_state, router):
        self.page = page
        self.state = app_state
        self.ui = ui_state
        self.router = router
        self._root: ft.Control = None
        self._snack_bar: ft.SnackBar = None
        self._last_snack_time = 0.0

    def build(self) -> ft.Control:
        return ft.Container(
            alignment=ft.Alignment.CENTER,
            content=ft.Text("未实现", size=TEXT_ML),
            expand=True,
        )

    def on_enter(self):
        pass

    def on_leave(self):
        pass

    # ═══ 轻量提示（SnackBar，自动消失，无需手动关闭）═══
    def _snack(self, msg: str, duration: int = 2500):
        """显示自动消失的 SnackBar 提示。

        SnackBar 加入 page.overlay，设 open=True 自动显示。
        若 500ms 内连续调用则复用现有 SnackBar，避免闪烁。
        """
        try:
            now = time.time()
            merged = now - self._last_snack_time < 0.5
            self._last_snack_time = now
            if merged and self._snack_bar is not None and hasattr(self._snack_bar, "content"):
                try:
                    self._snack_bar.content.value = msg
                    self._snack_bar.duration = duration
                    self._snack_bar.open = True
                    self.page.update()
                    return
                except Exception:
                    pass
            # 移除旧的 SnackBar
            if self._snack_bar is not None:
                try:
                    self._snack_bar.open = False
                    if self._snack_bar in self.page.overlay:
                        self.page.overlay.remove(self._snack_bar)
                except Exception:
                    pass
            sb = ft.SnackBar(
                content=ft.Text(msg, size=TEXT_SM),
                duration=duration,
                show_close_icon=True,
            )
            self._snack_bar = sb
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
        except Exception:
            pass
