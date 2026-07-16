# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · 拖拽排序发言顺序
  ▼ 参与对话：Draggable + DragTarget 列表，每行 ☰ ●名字 [✕]
  ▼ 待命角色：OutlinedChip 点+加入
  🔒 你（用户模式自动加入，锁定）
  拖拽源行半透明，目标位高亮。on_accept 交换 state.turn_order 后 _save_turn_order()。
"""

import flet as ft

from app.theme import char_color_at, RADIUS_PILL

__all__ = ["TurnOrderEditor"]

_MODES = [("轮流", "round"), ("随机", "random"), ("动态", "dynamic")]


class TurnOrderEditor:
    """发言顺序编辑器（拖拽排序）。"""

    def __init__(self, page: ft.Page, state):
        self.page = page
        self.state = state
        self._dragging: int = None  # 当前拖拽源索引
        self._mode_dd: ft.Dropdown = None
        self._active_col: ft.Column = None
        self._standby_row: ft.Row = None
        self.root = self._build()

    def _build(self) -> ft.Control:
        self._active_col = ft.Column(spacing=6, tight=True)
        self._standby_row = ft.Row(spacing=8, wrap=True)
        return ft.Column(
            controls=[
                ft.Container(height=4),
                ft.Text("参与对话", size=12, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                self._active_col,
                ft.Container(height=4),
                ft.Text("待命角色（点击加入）", size=12, weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE_VARIANT),
                self._standby_row,
            ],
            spacing=4,
            tight=True,
        )

    def refresh(self):
        self._build_active()
        self._build_standby()
        try:
            self.page.update()
        except Exception:
            pass

    def _build_active(self):
        order = list(self.state.turn_order)
        total = max(1, len([n for n in order if n in self.state.characters and n != "You"]))
        rows = []
        for i, name in enumerate(order):
            if name not in self.state.characters:
                continue
            # 用户模式下 You 由锁定行显示，不生成普通行（避免重复）
            if name == "You" and self.state.user_mode:
                continue
            rows.append(self._make_row(i, name, total))
        # 你锁定行（用户模式 + You 在顺序中）
        if "You" in self.state.characters and self.state.user_mode and "You" in order:
            rows.append(self._locked_you_row())
        self._active_col.controls = rows

    def _build_standby(self):
        order = set(self.state.turn_order)
        standby = [n for n in self.state.characters if n not in order and n != "You"]
        if not standby:
            self._standby_row.controls = [ft.Text("无", size=11, color=ft.Colors.ON_SURFACE_VARIANT)]
            return
        chips = []
        for n in standby:
            c = self.state.characters[n]
            dname = c.get("display_name", n)
            chips.append(ft.Chip(
                label=ft.Text(dname, size=12),
                leading=ft.Icon(ft.Icons.ADD, size=14),
                on_click=self._make_add(n),
            ))
        self._standby_row.controls = chips

    def _make_add(self, name):
        def handler(e):
            self.state.turn_order.append(name)
            try:
                self.state.data._save_turn_order()
            except Exception:
                pass
            self.refresh()
        return handler

    def _make_row(self, index: int, name: str, total: int) -> ft.Control:
        c = self.state.characters.get(name, {})
        dname = c.get("display_name", name)
        is_you = name == "You"
        # 角色色点
        non_you = [n for n in self.state.turn_order if n in self.state.characters and n != "You"]
        color_idx = non_you.index(name) if name in non_you else 0
        color = char_color_at(color_idx, max(1, len(non_you)))
        dot = ft.Container(width=10, height=10, border_radius=5, bgcolor=color)

        # You 行不显示移除按钮（用户模式下由锁定行处理；非用户模式下不应出现）
        trailing = ft.Container(width=4)
        if not is_you:
            trailing = ft.IconButton(
                icon=ft.Icons.CLOSE, icon_size=16,
                tooltip="移除",
                on_click=self._make_remove(name),
            )

        card = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.DRAG_HANDLE, size=18, color=ft.Colors.ON_SURFACE_VARIANT),
                    dot,
                    ft.Text(dname, size=13, weight=ft.FontWeight.W_500, expand=True),
                    trailing,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            border=ft.Border.all(1, ft.Colors.TRANSPARENT),
        )

        drag = ft.Draggable(
            group="turn_order",
            content=card,
            content_when_dragging=ft.Container(
                content=card, opacity=0.35,
            ),
            data=str(index),
            on_drag_start=lambda e, idx=index: setattr(self, "_dragging", idx),
        )
        target = ft.DragTarget(
            group="turn_order",
            content=drag,
            on_will_accept=self._make_will(index),
            on_accept=self._make_accept(index),
            on_leave=self._make_leave(index),
        )
        return target

    def _locked_you_row(self) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.LOCK, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text("你（用户模式自动加入）", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                spacing=8,
            ),
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        )

    def _make_remove(self, name):
        def handler(e):
            if name == "You":
                return
            if name in self.state.turn_order:
                self.state.turn_order.remove(name)
                try:
                    self.state.data._save_turn_order()
                except Exception:
                    pass
                self.refresh()
        return handler

    def _make_will(self, index):
        def handler(e):
            # 高亮目标位
            try:
                tgt = e.control
                tgt.content.content.border = ft.Border.all(2, ft.Colors.PRIMARY)
                self.page.update()
            except Exception:
                pass
        return handler

    def _make_leave(self, index):
        def handler(e):
            try:
                tgt = e.control
                tgt.content.content.border = ft.Border.all(1, ft.Colors.TRANSPARENT)
                self.page.update()
            except Exception:
                pass
        return handler

    def _make_accept(self, target_index):
        def handler(e):
            src = self._dragging
            try:
                e.control.content.content.border = ft.Border.all(1, ft.Colors.TRANSPARENT)
            except Exception:
                pass
            if src is None or src == target_index:
                self._dragging = None
                return
            order = list(self.state.turn_order)
            if 0 <= src < len(order) and 0 <= target_index < len(order):
                item = order.pop(src)
                order.insert(target_index, item)
                self.state.turn_order = order
                try:
                    self.state.data._save_turn_order()
                except Exception:
                    pass
            self._dragging = None
            self.refresh()
        return handler
