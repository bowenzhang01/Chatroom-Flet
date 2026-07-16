# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 路由与响应式导航
  桌面(≥900px)：左侧 NavigationRail(72px) + 右侧内容区
  手机(<900px)：顶部 AppBar + 底部 NavigationBar
  4 个视图：/chat /profiles /archives /settings
"""

import flet as ft

from app.views.chat_view import ChatView
from app.views.profiles_view import ProfilesView
from app.views.archives_view import ArchivesView
from app.views.settings_view import SettingsView

__all__ = ["AppRouter", "NAV_ITEMS"]

# ── 导航项 ──
NAV_ITEMS = [
    {"route": "/chat", "icon": ft.Icons.CHAT_BUBBLE_OUTLINE, "selected_icon": ft.Icons.CHAT_BUBBLE, "label": "聊天"},
    {"route": "/profiles", "icon": ft.Icons.MENU_BOOK_OUTLINED, "selected_icon": ft.Icons.MENU_BOOK, "label": "剧本"},
    {"route": "/archives", "icon": ft.Icons.FOLDER_OUTLINED, "selected_icon": ft.Icons.FOLDER, "label": "存档"},
    {"route": "/settings", "icon": ft.Icons.SETTINGS_OUTLINED, "selected_icon": ft.Icons.SETTINGS, "label": "设置"},
]


class AppRouter:
    """路由控制器 + 响应式壳。"""

    def __init__(self, page: ft.Page, app_state, ui_state):
        self.page = page
        self.state = app_state
        self.ui = ui_state
        self._views = {}  # route -> view control
        self._current_route: str = None
        self._rail: ft.NavigationRail = None
        self._navbar: ft.NavigationBar = None
        self._content: ft.Control = None
        self._root: ft.Control = None

    # ═══ 构建壳 ═══
    def build(self):
        self.page.on_resize = self._on_resize
        self.page.on_route_change = self._on_route_change
        self.page.on_view_pop = self._on_view_pop

        self._build_shell()
        self.page.add(self._root)
        self.page.navigate(self.ui.route)

    def _build_shell(self):
        desktop = self.ui.is_desktop(self.page)
        if desktop:
            self._build_desktop()
        else:
            self._build_mobile()

    # ── 桌面：NavigationRail + 内容 ──
    def _build_desktop(self):
        self._rail = ft.NavigationRail(
            selected_index=0,
            min_width=72,
            min_extended_width=200,
            label_type=ft.NavigationRailLabelType.ALL,
            group_alignment=0.0,
            destinations=[
                ft.NavigationRailDestination(
                    icon=it["icon"], selected_icon=it["selected_icon"], label=it["label"]
                ) for it in NAV_ITEMS
            ],
            on_change=self._on_rail_change,
        )
        self._content = ft.Container(expand=True, padding=0)
        self._root = ft.Row(
            controls=[self._rail, ft.VerticalDivider(width=1), self._content],
            spacing=0,
            expand=True,
        )

    # ── 手机：内容 + 底部 NavigationBar（视图自带顶部 header）──
    def _build_mobile(self):
        self._content = ft.Container(expand=True, padding=0)
        self._navbar = ft.NavigationBar(
            selected_index=0,
            destinations=[
                ft.NavigationBarDestination(icon=it["icon"], selected_icon=it["selected_icon"], label=it["label"])
                for it in NAV_ITEMS
            ],
            on_change=self._on_navbar_change,
        )
        self._root = ft.Column(
            controls=[self._content, self._navbar],
            spacing=0,
            expand=True,
        )

    # ═══ 视图工厂 ═══
    def _get_view(self, route: str):
        if route not in self._views:
            v = self._make_view(route)
            v._root = v.build()  # 构建根 ft.Control
            self._views[route] = v
        return self._views[route]

    def _make_view(self, route: str) -> ft.Control:
        if route == "/chat":
            return ChatView(self.page, self.state, self.ui, self)
        if route == "/profiles":
            return ProfilesView(self.page, self.state, self.ui, self)
        if route == "/archives":
            return ArchivesView(self.page, self.state, self.ui, self)
        if route == "/settings":
            return SettingsView(self.page, self.state, self.ui, self)
        return ChatView(self.page, self.state, self.ui, self)

    # ═══ 路由切换 ═══
    def _route_to_index(self, route: str) -> int:
        for i, it in enumerate(NAV_ITEMS):
            if it["route"] == route:
                return i
        return 0

    def _index_to_route(self, index: int) -> str:
        if 0 <= index < len(NAV_ITEMS):
            return NAV_ITEMS[index]["route"]
        return "/chat"

    def navigate(self, route: str):
        self.page.navigate(route)

    def get_view(self, route: str):
        """获取已缓存的视图实例（供跨视图调用）。"""
        return self._views.get(route)

    # ═══ 事件 ═══
    def _on_route_change(self, e):
        route = self.page.route or "/chat"
        # 离开旧视图
        if self._current_route and self._current_route != route:
            old = self._views.get(self._current_route)
            if old and hasattr(old, "on_leave"):
                try:
                    old.on_leave()
                except Exception as ex:
                    print(f"[router] on_leave {self._current_route} 异常: {ex}")
        self._current_route = route
        self.ui.route = route
        idx = self._route_to_index(route)
        if self._rail:
            self._rail.selected_index = idx
        if self._navbar:
            self._navbar.selected_index = idx
        view = self._get_view(route)
        self._content.content = view._root
        # 视图激活回调
        if hasattr(view, "on_enter"):
            try:
                view.on_enter()
            except Exception as ex:
                print(f"[router] on_enter {route} 异常: {ex}")
        self.page.update()

    def _on_rail_change(self, e):
        self.page.navigate(self._index_to_route(e.control.selected_index))

    def _on_navbar_change(self, e):
        self.page.navigate(self._index_to_route(e.control.selected_index))

    def _on_view_pop(self, e):
        self.page.navigate("/chat")

    def _on_resize(self, e):
        desktop = self.ui.is_desktop(self.page)
        was_desktop = self._rail is not None
        if desktop != was_desktop:
            # 重建壳
            self.page.controls.clear()
            self._rail = None
            self._navbar = None
            self._build_shell()
            self.page.add(self._root)
            # 重新应用当前路由
            route = self.ui.route
            idx = self._route_to_index(route)
            if self._rail:
                self._rail.selected_index = idx
            if self._navbar:
                self._navbar.selected_index = idx
            view = self._get_view(route)
            self._content.content = view._root
            if hasattr(view, "on_enter"):
                try:
                    view.on_enter()
                except Exception as ex:
                    print(f"[router] on_enter (resize) {route} 异常: {ex}")
            self.page.update()

    # ═══ 主题刷新 ═══
    def apply_theme(self):
        self.page.theme_mode = self.ui.theme_mode()
        self.page.update()
