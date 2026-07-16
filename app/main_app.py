# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 应用入口组装
  main(page): 注册字体 → 创建 AppState + UIState → 应用主题 → 装配路由
"""

import flet as ft

import config
from app.theme import build_theme, COLORS
from app.state import UIState
from app.router import AppRouter


def main(page: ft.Page):
    # ── 字体注册 ──
    page.fonts = {config.FONT_SC_NAME: str(config.FONT_SC_PATH)}
    page.font_family = config.FONT_SC_NAME

    # ── 业务层 + UI 状态 ──
    from core.app_state import AppState
    app_state = AppState()
    app_state.init_workspace()
    ui_state = UIState()
    ui_state.load_theme_mode()

    # ── 主题 ──
    page.theme = build_theme(ui_state.color_theme_key, "light")
    page.dark_theme = build_theme(ui_state.color_theme_key, "dark")
    page.theme_mode = ui_state.theme_mode()

    # ── 窗口默认 ──
    page.title = "ChatRoom"
    page.window.width = 1200
    page.window.height = 800
    page.window.min_width = 380
    page.window.min_height = 600
    page.padding = 0

    # ── 路由装配 ──
    router = AppRouter(page, app_state, ui_state)
    page.app_state = app_state  # 便于测试/跨视图访问
    page.ui_state = ui_state
    page.router = router
    router.build()

    # ── 启动后检查自动存档（延迟，确保 chat_view 已订阅事件）──
    import threading

    def _delayed_autosave_check():
        import time as _time
        _time.sleep(0.6)
        try:
            app_state.check_autosave_on_start()
        except Exception as e:
            print(f"[startup] check_autosave 失败: {e}")

    threading.Thread(target=_delayed_autosave_check, daemon=True).start()

    # ── 生命周期：自动存档 ──
    def _on_window_event(e):
        if e.type == ft.WindowEventType.CLOSE:
            try:
                app_state.auto_save()
            except Exception:
                pass

    page.window.on_event = _on_window_event
    page.on_disconnect = lambda e: app_state.auto_save()
