# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · 角色卡
  CircleAvatar（色点+首字）+ 名字 + 英文名 + 描述2行 + [✨补全][⋮]
  另含「+ 新角色」卡、「✨ AI 生成」卡（由 profiles_view 拼装）。
"""

import flet as ft

from app.theme import char_color_at, RADIUS_CARD, TEXT_ML, TEXT_MD, TEXT_SM, TEXT_XS

__all__ = ["CharacterCard", "AddCharacterCard", "AIGenerateCharacterCard"]


class CharacterCard:
    """角色卡。on_edit(name) / on_ai_complete(name) / on_menu(action, name) 回调。"""

    def __init__(self, page: ft.Page, char: dict, index: int, total: int,
                 on_edit=None, on_ai=None, on_menu=None):
        self.page = page
        self.char = char
        self.on_edit = on_edit
        self.on_ai = on_ai
        self.on_menu = on_menu
        self.root = self._build(index, total)

    def _build(self, index: int, total: int) -> ft.Control:
        name = self.char.get("name", "?")
        dname = self.char.get("display_name", name)
        en = self.char.get("name", "")
        desc = self.char.get("description", "") or self.char.get("personality", "")
        color = self.char.get("color") or char_color_at(index, total)
        initial = (dname or name or "?")[0]
        is_you = name == "You"

        avatar = ft.CircleAvatar(
            content=ft.Text(initial, size=TEXT_ML, color=ft.Colors.WHITE, weight=ft.FontWeight.W_700),
            bgcolor=color, radius=20,
        )
        if is_you:
            menu_items = [
                ft.PopupMenuItem(content=ft.Text("编辑"), icon=ft.Icons.EDIT,
                                 on_click=lambda e: self._edit()),
            ]
        else:
            menu_items = [
                ft.PopupMenuItem(content=ft.Text("编辑"), icon=ft.Icons.EDIT,
                                 on_click=lambda e: self._edit()),
                ft.PopupMenuItem(content=ft.Text("删除"), icon=ft.Icons.DELETE_OUTLINE,
                                 on_click=lambda e: self._menu("delete")),
                ft.PopupMenuItem(content=ft.Text("复制"), icon=ft.Icons.CONTENT_COPY,
                                 on_click=lambda e: self._menu("duplicate")),
            ]
        menu_btn = ft.PopupMenuButton(icon=ft.Icons.MORE_VERT, items=menu_items)

        header_controls = [
            avatar,
            ft.Column(
                controls=[
                    ft.Text(dname, size=TEXT_MD, weight=ft.FontWeight.W_600, max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(en, size=TEXT_XS, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=1),
                ],
                spacing=0, tight=True,
            ),
        ]
        if is_you:
            header_controls.append(
                ft.Container(
                    content=ft.Text("👤 你", size=TEXT_XS, color=ft.Colors.PRIMARY),
                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                    border_radius=8,
                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                )
            )

        card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=header_controls,
                            spacing=10,
                        ),
                        ft.Text(desc, size=TEXT_XS, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row(
                            controls=[
                                ft.TextButton(
                                    content=ft.Text("补全"),
                                    icon=ft.Icons.AUTO_AWESOME,
                                    style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=8, vertical=4)),
                                    on_click=lambda e: self._ai(),
                                ),
                                menu_btn,
                            ],
                            spacing=0,
                            wrap=False,
                        ),
                    ],
                    spacing=6,
                    tight=True,
                ),
                padding=ft.Padding.all(12),
            ),
            elevation=0,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        )
        return ft.Container(content=card, on_click=lambda e: self._edit())

    def _edit(self):
        if self.on_edit:
            try: self.on_edit(self.char.get("name"))
            except Exception: pass

    def _ai(self):
        if self.on_ai:
            try: self.on_ai(self.char.get("name"))
            except Exception: pass

    def _menu(self, action: str):
        if self.on_menu:
            try: self.on_menu(action, self.char.get("name"))
            except Exception: pass


class AddCharacterCard:
    """＋ 新角色卡。"""

    def __init__(self, page: ft.Page, on_add=None):
        self.page = page
        self.on_add = on_add
        self.root = self._build()

    def _build(self) -> ft.Control:
        card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.PERSON_ADD, size=28, color=ft.Colors.PRIMARY),
                        ft.Text("新角色", size=TEXT_SM, weight=ft.FontWeight.W_500),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                ),
                padding=ft.Padding.all(16),
                alignment=ft.Alignment.CENTER,
                expand=True,
            ),
            elevation=0,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        )
        return ft.Container(content=card, on_click=lambda e: self._add(), expand=True)

    def _add(self):
        if self.on_add:
            try: self.on_add()
            except Exception: pass


class AIGenerateCharacterCard:
    """✨ AI 生成角色卡。"""

    def __init__(self, page: ft.Page, on_generate=None):
        self.page = page
        self.on_generate = on_generate
        self.root = self._build()

    def _build(self) -> ft.Control:
        card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.AUTO_AWESOME, size=28, color=ft.Colors.SECONDARY),
                        ft.Text("AI 生成", size=TEXT_SM, weight=ft.FontWeight.W_500),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                ),
                padding=ft.Padding.all(16),
                alignment=ft.Alignment.CENTER,
                expand=True,
            ),
            elevation=0,
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
        )
        return ft.Container(content=card, on_click=lambda e: self._gen(), expand=True)

    def _gen(self):
        if self.on_generate:
            try: self.on_generate()
            except Exception: pass
