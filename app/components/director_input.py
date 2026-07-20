# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · 底部输入栏（导演 / 用户）
  导演模式：TextField + 发送 → state.loop.send_director_note(text)
  用户回合：TextField + 发送 + 跳过 → state.loop.send_user_message(text) / skip_user_turn()
  仅在对应模式时滑入（由 chat_view 控制 show/hide）。
"""

import threading

import flet as ft

from app.theme import RADIUS_PILL

__all__ = ["DirectorInput"]


class DirectorInput:
    """底部输入栏。mode: 'director' | 'user' | None(隐藏)。"""

    def __init__(self, page: ft.Page, state):
        self.page = page
        self.state = state
        self.mode: str = None
        self._field: ft.TextField = None
        self._send_btn: ft.FilledButton = None
        self._skip_btn: ft.TextButton = None
        self._hint: ft.Text = None
        self._feedback_timer: threading.Timer = None
        # 持有 asyncio loop 引用（在主线程构造时捕获），供后台线程调度 coroutine
        import asyncio
        try:
            self._async_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._async_loop = None
        self.root = self._build()

    def _build(self) -> ft.Control:
        self._hint = ft.Text("", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
        self._field = ft.TextField(
            hint_text="输入内容…",
            multiline=False,
            dense=True,
            border_radius=RADIUS_PILL,
            expand=True,
            on_submit=lambda e: self._send(),
        )
        self._send_btn = ft.FilledButton(
            content=ft.Text("发送"),
            icon=ft.Icons.SEND,
            on_click=lambda e: self._send(),
        )
        self._skip_btn = ft.TextButton(
            content=ft.Text("跳过"),
            icon=ft.Icons.SKIP_NEXT,
            on_click=lambda e: self._skip(),
            visible=False,
        )
        return ft.Container(
            content=ft.Column(
                controls=[
                    self._hint,
                    ft.Row(
                        controls=[self._field, self._send_btn, self._skip_btn],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=4,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            visible=False,
            opacity=0.0,
            animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
            offset=ft.Offset(0, 0.08),
            animate_offset=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
        )

    # ═══ 显示控制 ═══
    def show(self, mode: str):
        self.mode = mode
        if mode == "director":
            self._hint.value = "导演提示 · 输入后会注入到对话"
            self._field.hint_text = "如：突然有人敲门"
            self._skip_btn.visible = False
        elif mode == "user":
            self._hint.value = "轮到你了 · 输入发言或跳过"
            self._field.hint_text = "说点什么…"
            self._skip_btn.visible = True
        else:
            self.hide()
            return
        self.root.visible = True
        self.root.opacity = 1.0
        self.root.offset = ft.Offset(0, 0)
        self._field.value = ""
        try:
            self.page.update()
        except Exception:
            pass
        self._try_focus()

    def hide(self):
        self.mode = None
        self.root.visible = False
        self.root.opacity = 0.0
        try:
            self.page.update()
        except Exception:
            pass

    def refresh(self, director_mode: bool, user_mode: bool, user_turn: bool):
        """根据状态自动决定显示模式。"""
        if user_turn:
            self.show("user")
        elif director_mode:
            self.show("director")
        else:
            self.hide()

    # ═══ 动作 ═══
    def _send(self):
        text = (self._field.value or "").strip()
        if not text:
            return
        if self.mode == "director":
            try:
                self.state.loop.send_director_note(text)
            except Exception as ex:
                print(f"[director_input] 发送导演提示失败: {ex}")
        elif self.mode == "user":
            try:
                self.state.loop.send_user_message(text)
            except Exception as ex:
                print(f"[director_input] 发送用户消息失败: {ex}")
        self._field.value = ""
        try:
            self.page.update()
        except Exception:
            pass
        # 导演模式发送后显示短暂反馈
        if self.mode == "director":
            self._show_sent_feedback()

    def _show_sent_feedback(self):
        saved_hint = self._hint.value
        saved_color = self._hint.color
        self._hint.value = "✓ 已发送"
        self._hint.color = ft.Colors.TERTIARY
        try:
            self.page.update()
        except Exception:
            pass
        def _reset():
            self._hint.value = saved_hint
            self._hint.color = saved_color
            try:
                self.page.update()
            except Exception:
                pass
        if self._feedback_timer:
            self._feedback_timer.cancel()
        self._feedback_timer = threading.Timer(1.5, _reset)
        self._feedback_timer.daemon = True
        self._feedback_timer.start()

    def _try_focus(self):
        try:
            result = self._field.focus()
            # Flet 在 Web 模式（有运行中的 asyncio loop）下 focus() 返回 coroutine；
            # 调 close() 会丢弃协程导致焦点不生效。
            # 正确处理：若是 coroutine，用 run_coroutine_threadsafe 跨线程安全调度到主 loop。
            # EventBus 事件由对话 loop 后台线程 emit，_try_focus 实际在后台线程执行，
            # 故必须在 __init__ 时捕获 _async_loop（主线程），此处用 call_soon_threadsafe 调度。
            if result is not None and self._async_loop is not None:
                try:
                    import asyncio
                    if asyncio.iscoroutine(result):
                        asyncio.run_coroutine_threadsafe(result, self._async_loop)
                except RuntimeError:
                    pass
        except Exception:
            pass

    def _skip(self):
        try:
            self.state.loop.skip_user_turn()
        except Exception as ex:
            print(f"[director_input] 跳过失败: {ex}")
        self._field.value = ""
        self.hide()
