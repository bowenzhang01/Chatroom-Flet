# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · 剧本封面卡
  封面 120px：主色渐变（蓝绿→蓝 / 蓝→紫）+ 代表性 emoji 大字
  信息：标题 / N角色·M场景 badges / 世界观 2 行 / K 个存档
  Card(border_radius=16, tonal bg)。长按/右键菜单：重命名/复制/删除/导出。
"""

import json
from pathlib import Path

import flet as ft

import config
from app.theme import RADIUS_CARD, profile_gradient, profile_emoji, char_color_at
from utils import load_json

__all__ = ["ProfileCard", "gather_profile_meta"]


def gather_profile_meta(folder_name: str) -> dict:
    """读取剧本元信息：display / characters / scenes / chats / world / emoji。"""
    pdir = config.PROFILES_DIR / folder_name
    pc = load_json(pdir / "config.json") or {}
    app = pc.get("app", {})
    title = app.get("title", folder_name)
    world = pc.get("world", {}).get("setting", "")
    order = pc.get("turn", {}).get("order", [])
    scenes = load_json(pdir / "scenes.json") or []
    char_dir = pdir / "characters"
    char_count = len(list(char_dir.glob("*.json"))) if char_dir.exists() else 0
    chats_dir = pdir / "chats"
    chat_count = len(list(chats_dir.glob("chat_*.json"))) if chats_dir.exists() else 0
    return {
        "folder": folder_name,
        "title": title,
        "world": world,
        "char_count": char_count,
        "scene_count": len(scenes),
        "chat_count": chat_count,
        "emoji": profile_emoji(folder_name, title),
        "order": order,
    }


class ProfileCard:
    """剧本封面卡。on_open(folder) / on_menu(action, folder) 回调。"""

    def __init__(self, page: ft.Page, meta: dict, on_open=None, on_menu=None):
        self.page = page
        self.meta = meta
        self.on_open = on_open
        self.on_menu = on_menu
        self.root = self._build()

    def _build(self) -> ft.Control:
        folder = self.meta["folder"]
        title = self.meta["title"]
        emoji = self.meta["emoji"]

        cover = ft.Container(
            content=ft.Text(emoji, size=44, text_align=ft.TextAlign.CENTER),
            gradient=profile_gradient(folder, title),
            height=120,
            alignment=ft.Alignment.CENTER,
            border_radius=ft.BorderRadius(top_left=RADIUS_CARD, top_right=RADIUS_CARD,
                                          bottom_left=0, bottom_right=0),
        )

        badges = ft.Row(
            controls=[
                self._badge(f"{self.meta['char_count']} 角色"),
                self._badge(f"{self.meta['scene_count']} 场景"),
            ],
            spacing=6,
        )
        world_text = self.meta["world"] or "暂无世界观"
        world = ft.Text(
            world_text, size=11, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        chats = ft.Text(
            f"{self.meta['chat_count']} 个存档", size=11, color=ft.Colors.ON_SURFACE_VARIANT,
        )

        menu_items = [
            ft.PopupMenuItem(content=ft.Text("重命名"), icon=ft.Icons.EDIT,
                             on_click=lambda e: self._menu("rename")),
            ft.PopupMenuItem(content=ft.Text("复制"), icon=ft.Icons.CONTENT_COPY,
                             on_click=lambda e: self._menu("duplicate")),
            ft.PopupMenuItem(content=ft.Text("导出"), icon=ft.Icons.UPLOAD_FILE,
                             on_click=lambda e: self._menu("export")),
            ft.PopupMenuItem(content=ft.Text("删除"), icon=ft.Icons.DELETE_OUTLINE,
                             on_click=lambda e: self._menu("delete")),
        ]
        menu_btn = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            items=menu_items,
        )

        title_row = ft.Row(
            controls=[
                ft.Container(content=ft.Text(title, size=15, weight=ft.FontWeight.W_700,
                                              max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                              expand=True),
                menu_btn,
            ],
            spacing=4,
        )
        info = ft.Container(
            content=ft.Column(
                controls=[title_row, badges, world, chats],
                spacing=4,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        )

        card = ft.Card(
            content=ft.Column(
                controls=[cover, info],
                spacing=0,
                tight=True,
            ),
            elevation=0,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        )
        return ft.Container(
            content=card,
            on_click=lambda e: self._open(),
            on_long_press=lambda e: self._menu("longpress"),
            padding=0,
        )

    def _badge(self, text: str) -> ft.Control:
        return ft.Container(
            content=ft.Text(text, size=10, color=ft.Colors.ON_SURFACE_VARIANT),
            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            border_radius=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        )

    def _open(self):
        if self.on_open:
            try:
                self.on_open(self.meta["folder"])
            except Exception:
                pass

    def _menu(self, action: str):
        if self.on_menu:
            try:
                self.on_menu(action, self.meta["folder"])
            except Exception:
                pass
