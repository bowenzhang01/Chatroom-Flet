# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · 聊天视图（主界面）
   组合：Header(剧本名·场景▾) + ModeChips + 内容区(空状态/气泡列表)
         + SceneBanner + 回到底部按钮 + TransportBar(含状态) + DirectorInput
   Step 3：骨架 + 空状态 + 模式 Chip + TransportBar + 状态栏
   Step 4：气泡渲染 + EventBus 接入
   Step 5：场景横幅 + 输入栏
"""

import flet as ft

import config
from app.views import ViewBase
from app.theme import RADIUS_PILL, profile_emoji, char_color_at
from app.components.mode_chips import ModeChips
from app.components.transport_bar import TransportBar
from app.components.chat_bubble import make_bubble_row, make_scene_change_row, render_streaming_text, _md
from app.components.scene_banner import SceneBanner
from app.components.director_input import DirectorInput
from app.components.progress_dialog import ProgressDialog

__all__ = ["ChatView"]


class ChatView(ViewBase):
    def __init__(self, page, app_state, ui_state, router):
        super().__init__(page, app_state, ui_state, router)
        self._mode_chips: ModeChips = None
        self._transport: TransportBar = None
        self._scene_banner: SceneBanner = None
        self._director_input: DirectorInput = None
        self._title_text: ft.Text = None
        self._scene_text: ft.Text = None
        self._status_dot: ft.Container = None
        self._status_text: ft.Text = None
        self._count_text: ft.Text = None
        self._empty_state: ft.Control = None
        self._content_stack: ft.Stack = None
        self._list_view: ft.ListView = None
        self._built = False
        self._subscribed = False
        self._dirty = True  # 首次进入需初始化；离开后需重新同步
        self._handlers = {}
        self._near_bottom = True
        self._has_msgs = False
        self._user_turn = False
        self._saving = False  # 保存防抖标记，防止重复点击
        self._save_dialog: ProgressDialog = None  # 保存进度对话框
        self._async_loop = None
        self._empty_title: ft.Text = None
        self._empty_emoji_text: ft.Text = None
        self._empty_avatars: ft.Control = None
        self._streaming_rows: dict = {}  # msg_id → ft.Row 映射
        self._streaming_count = 0  # 活跃的流式气泡数，_on_scroll 据此抑制按钮闪烁
        self._bottom_btn_visible = False  # 按钮是否已插入 Column

    # ═══ 构建视图 ═══
    def build(self) -> ft.Control:
        self._mode_chips = ModeChips(self.page, self.state, on_change=self._on_mode_change)

        # 状态指示器（合并到 TransportBar 中）
        self._status_dot = ft.Container(
            width=8, height=8, border_radius=4,
            bgcolor=ft.Colors.OUTLINE,
        )
        self._status_text = ft.Text("就绪", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._count_text = ft.Text("0 条", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

        self._transport = TransportBar(
            self.page, self.state, on_action=self._on_transport_action,
            extra_controls=[
                ft.Container(width=8),
                self._status_dot,
                self._status_text,
                ft.Container(width=8),
                self._count_text,
            ],
        )
        self._scene_banner = SceneBanner(self.page)
        self._director_input = DirectorInput(self.page, self.state)

        import asyncio
        try:
            self._async_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._async_loop = None

        self._to_bottom_btn = ft.Container(
            content=ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ARROW_DOWNWARD,
                        icon_size=18,
                        tooltip="回到底部",
                        on_click=lambda e: self._scroll_to_bottom(),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                            shape=ft.CircleBorder(),
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.Padding.only(bottom=8, top=4),
        )

        self._root = ft.Column(
            controls=[
                self._build_header(),
                self._mode_chips.root,
                self._build_content(),
                self._transport.root,
                self._director_input.root,
            ],
            spacing=0,
            expand=True,
        )
        self._built = True
        return self._root

    def _push_update(self):
        try:
            if self._async_loop and self._async_loop.is_running():
                self._async_loop.call_soon_threadsafe(self.page.update)
            else:
                self.page.update()
        except Exception:
            pass

    # ── Header ──
    def _build_header(self) -> ft.Control:
        self._title_text = ft.Text(
            self.state.title, size=18, weight=ft.FontWeight.W_700, max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self._scene_text = ft.Text(
            self._scene_label(), size=13, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        title_btn = ft.PopupMenuButton(
            content=ft.Row(
                controls=[
                    self._title_text,
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=20, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                spacing=2,
            ),
            items=self._build_header_menu_items(),
            on_open=self._refresh_header_menu,
        )
        scene_btn = ft.Container(
            content=ft.Row([self._scene_text], spacing=4),
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            border_radius=RADIUS_PILL,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            on_click=lambda e: self._show_scene_dialog(),
        )

        theme_btn = ft.IconButton(
            icon=ft.Icons.DARK_MODE_OUTLINED,
            selected_icon=ft.Icons.LIGHT_MODE_OUTLINED,
            selected=(self.ui.theme_mode_key == "dark"),
            tooltip="切换主题",
            on_click=self._toggle_theme,
        )
        settings_btn = ft.IconButton(
            icon=ft.Icons.SETTINGS_OUTLINED,
            tooltip="设置",
            on_click=lambda e: self.router.navigate("/settings"),
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    title_btn,
                    scene_btn,
                    ft.Container(expand=True),
                    theme_btn,
                    settings_btn,
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            bgcolor=ft.Colors.SURFACE,
        )

    def _build_header_menu_items(self) -> list:
        items = []
        profiles = self.state.data.get_profile_list()
        if len(profiles) > 1:
            items.append(ft.PopupMenuItem(content=ft.Text("切换剧本"), icon=ft.Icons.MENU_BOOK, on_click=self._go_profiles))
        items.append(ft.PopupMenuItem(content=ft.Text("管理剧本"), icon=ft.Icons.EDIT, on_click=self._go_profiles))
        items.append(ft.PopupMenuItem())
        items.append(ft.PopupMenuItem(content=ft.Text("场景设置"), icon=ft.Icons.PLACE_OUTLINED, on_click=lambda e: self._show_scene_dialog()))
        return items

    def _refresh_header_menu(self, e=None):
        if self._title_text:
            self._title_text.value = self.state.title
        if self._scene_text:
            self._scene_text.value = self._scene_label()
        try:
            if self._title_text:
                self._title_text.update()
            if self._scene_text:
                self._scene_text.update()
        except Exception:
            pass

    # ── 内容区（空状态 + 气泡列表 + banner slot）──
    def _build_content(self) -> ft.Control:
        self._empty_state = self._build_empty_state()
        self._list_view = ft.ListView(
            controls=[],
            expand=True,
            spacing=8,
            padding=ft.Padding.symmetric(horizontal=8, vertical=8),
            auto_scroll=True,
            on_scroll=self._on_scroll,
        )
        self._content_stack = ft.Stack(
            controls=[self._list_view, self._empty_state, self._scene_banner.root],
            expand=True,
        )
        return ft.Container(
            content=self._content_stack,
            expand=True,
            padding=ft.Padding.symmetric(horizontal=0, vertical=0),
        )

    def _bubble_max_width(self) -> float:
        w = self.page.width or 600
        # 减去导航栏宽 + 头像 + 内边距
        if self.ui.is_desktop(self.page):
            w = max(220, w - 72 - 16 - 60)
        else:
            w = max(200, w - 16 - 60)
        return min(w * 0.62, 520)

    def _on_scroll(self, e):
        try:
            pixels = float(getattr(e, "pixels", 0) or 0)
            max_ext = float(getattr(e, "max_scroll_extent", 0) or 0)
            self._near_bottom = (max_ext - pixels) < 120
            self._list_view.auto_scroll = self._near_bottom
            if self._streaming_count == 0:
                self._sync_bottom_btn(not self._near_bottom)
        except Exception:
            pass

    def _build_empty_state(self) -> ft.Control:
        folder = config.app_config.get("active_profile", "")
        emoji = profile_emoji(folder, self.state.title)
        title = ft.Text(self.state.title, size=22, weight=ft.FontWeight.W_700, text_align=ft.TextAlign.CENTER)
        subtitle = ft.Text("对话尚未开始", size=13, color=ft.Colors.ON_SURFACE_VARIANT)
        avatars = self._build_character_avatars()
        start_btn = ft.FilledButton(
            content=ft.Text("开始对话"),
            icon=ft.Icons.PLAY_ARROW,
            on_click=lambda e: self._on_transport_action("start"),
        )

        self._empty_title = title
        self._empty_avatars = avatars
        self._empty_emoji_text = ft.Text(emoji, size=56, text_align=ft.TextAlign.CENTER)

        col = ft.Column(
            controls=[
                ft.Container(height=24),
                self._empty_emoji_text,
                title,
                subtitle,
                ft.Container(height=8),
                self._characters_divider(),
                avatars,
                ft.Container(height=16),
                start_btn,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
            scroll=ft.ScrollMode.AUTO,
        )
        return ft.Container(
            content=col,
            alignment=ft.Alignment.CENTER,
            expand=True,
            padding=ft.Padding.all(24),
        )

    def _build_character_avatars(self) -> ft.Control:
        chars = [c for n, c in self.state.characters.items()]
        if not chars:
            return ft.Text("暂无角色", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        total = len(chars)
        avatars = []
        for i, c in enumerate(chars):
            color = char_color_at(i, total)
            dname = c.get("display_name", c.get("name", "?"))
            initial = dname[0] if dname else "?"
            avatars.append(ft.Column(
                controls=[
                    ft.CircleAvatar(
                        content=ft.Text(initial, size=14, color=ft.Colors.WHITE, weight=ft.FontWeight.W_700),
                        bgcolor=color,
                        radius=16,
                    ),
                    ft.Text(dname, size=11, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=1),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ))
        return ft.Row(
            controls=avatars,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=16,
            wrap=True,
        )

    def _characters_divider(self) -> ft.Control:
        return ft.Row(
            controls=[
                ft.Container(expand=True, content=ft.Divider(height=1)),
                ft.Text("参与角色", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Container(expand=True, content=ft.Divider(height=1)),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        )

    def _rebuild_empty_state(self):
        folder = config.app_config.get("active_profile", "")
        emoji = profile_emoji(folder, self.state.title)
        if self._empty_emoji_text:
            self._empty_emoji_text.value = emoji
        if self._empty_title:
            self._empty_title.value = self.state.title
        new_avatars = self._build_character_avatars()
        if self._empty_avatars and new_avatars:
            parent = self._empty_avatars.parent
            if parent is not None and hasattr(parent, 'controls'):
                idx = parent.controls.index(self._empty_avatars)
                parent.controls[idx] = new_avatars
                self._empty_avatars = new_avatars

    def _reset_to_empty(self):
        self._list_view.controls.clear()
        self._has_msgs = False
        self._empty_state.visible = True
        self._rebuild_empty_state()
        self._update_status("就绪", False, False)
        if self._count_text:
            self._count_text.value = "0 条"
        try:
            self.page.update()
        except Exception:
            pass

    # ═══ 场景/剧本 ═══
    def _scene_label(self) -> str:
        s = self.state.current_scene
        if s and s.get("time"):
            return f"📍 {s.get('time', '')} · {s.get('location', '')}".strip(" ·")
        if self.state.scene_idx == -1:
            return "📍 按时间生成"
        if self.state.scenes:
            idx = self.state.scene_idx
            if 0 <= idx < len(self.state.scenes):
                sc = self.state.scenes[idx]
            else:
                sc = self.state.scenes[0]
            return f"📍 {sc.get('time', '')} · {sc.get('location', '')}".strip(" ·")
        return "📍 未设置场景"

    def _go_profiles(self, e=None):
        self.router.navigate("/profiles")

    def _show_scene_dialog(self):
        scenes = self.state.scenes or []
        if not scenes:
            self._snack("暂无场景，请先到剧本管理中添加场景")
            return
        controls = [
            ft.ListTile(
                leading=ft.Icon(ft.Icons.SCHEDULE),
                title=ft.Text("⏱ 按现实时间生成"),
                on_click=self._make_time_scene_handler(),
            ),
            ft.Divider(height=1),
        ]
        for i, sc in enumerate(scenes):
            controls.append(ft.ListTile(
                leading=ft.Icon(ft.Icons.PLACE_OUTLINED),
                title=ft.Text(f"{sc.get('time', '')} · {sc.get('location', '')}"),
                subtitle=ft.Text(sc.get("mood", ""), size=11),
                on_click=self._make_scene_pick_handler(i),
            ))
        dlg = ft.AlertDialog(
            title=ft.Text("选择场景"),
            content=ft.Column(controls=controls, tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("取消", on_click=lambda e: self._close_dialog())],
        )
        self.page.show_dialog(dlg)

    def _make_time_scene_handler(self):
        def handler(e):
            self.state.scene_idx = -1
            self.state.loop._on_manual_scene_switch()
            self._close_dialog()
            self._refresh_header_menu()
        return handler

    def _make_scene_pick_handler(self, idx):
        def handler(e):
            self.state.scene_idx = idx
            self.state.loop._on_manual_scene_switch()
            self._close_dialog()
            self._refresh_header_menu()
        return handler

    def _close_dialog(self):
        try:
            self.page.pop_dialog()
        except Exception:
            pass

    # ═══ 模式 / 传输 ═══
    def _on_mode_change(self, attr, value):
        # 导演/用户模式切换时刷新输入栏可见性
        self._director_input.refresh(
            self.state.director_mode, self.state.user_mode, self._user_turn
        )

    def _on_transport_action(self, action):
        if action == "start":
            try:
                self.state.loop.start()
            except Exception as ex:
                print(f"[chat] 启动失败: {ex}")
                self._update_status(f"启动失败: {ex}", False, False)
        elif action == "pause":
            self.state.loop.pause()
        elif action == "resume":
            self.state.loop.resume()
        elif action == "stop":
            self._confirm_stop()
        elif action == "save":
            self._do_save()

    def _do_save(self):
        # 防抖：保存进行中时忽略后续点击
        if self._saving:
            return
        if not self.state.history:
            self._snack("没有对话内容可保存")
            return
        self._saving = True
        # 超时兜底：30s 后强制复位，防止 AI 标题生成挂起导致按钮永久禁用
        def _save_timeout():
            import time as _t
            _t.sleep(30)
            if self._saving:
                self._saving = False
                if self._save_dialog:
                    self._save_dialog.fail("保存超时，请重试")
                    self._save_dialog = None
                self._update_status("保存超时，请重试", self.state.running, self.state.paused)
        import threading
        threading.Thread(target=_save_timeout, daemon=True).start()
        # 即时反馈：禁用保存按钮 + 状态栏提示
        self._update_status("正在保存…", self.state.running, self.state.paused)
        # 显示保存进度对话框
        self._save_dialog = ProgressDialog(self.page, title="💾 保存对话")
        self._save_dialog.show(
            status="正在写入对话数据…",
            steps=["写入对话数据", "生成对话标题", "完成"],
            indeterminate=True,
        )
        self._save_dialog.set_step(0, "正在写入对话数据…")
        try:
            self.state.chat.save_current_chat()
        except Exception as ex:
            print(f"[chat] 保存失败: {ex}")
            if self._save_dialog:
                self._save_dialog.fail("保存失败：" + str(ex)[:60])
            self._saving = False

    def _confirm_stop(self):
        unsaved = self.state.chat.has_unsaved_messages() if hasattr(self.state.chat, "has_unsaved_messages") else False
        count = self.state.message_count

        def do_stop(e=None):
            self.state.loop.stop()
            self._close_dialog()
            self._transport.set_running(False, False)

        dlg = ft.AlertDialog(
            title=ft.Text("停止对话"),
            content=ft.Text(f"当前对话有 {count} 条消息" + ("，部分未保存" if unsaved else "")),
            actions=[
                ft.FilledButton("保存并停止", on_click=lambda e: self._save_then_stop(do_stop)),
                ft.TextButton("直接停止", on_click=do_stop),
                ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
            ],
        )
        self.page.show_dialog(dlg)

    def _save_then_stop(self, after):
        # 先关闭停止确认对话框（不能让 after 的 _close_dialog 误关进度对话框）
        self._close_dialog()
        # 显示保存进度对话框（_on_saved 事件会更新它）
        self._saving = True
        self._save_dialog = ProgressDialog(self.page, title="💾 保存对话")
        self._save_dialog.show(
            status="正在写入对话数据…",
            steps=["写入对话数据", "生成对话标题", "停止对话"],
            indeterminate=True,
        )
        self._save_dialog.set_step(0, "正在写入对话数据…")
        # 先保存（快照数据），再停止（stop 会清空 history）
        try:
            self.state.chat.save_current_chat()
        except Exception:
            pass
        # 立即停止对话（保存数据已快照，AI 标题异步生成不受影响）
        self.state.loop.stop()
        self._transport.set_running(False, False)

    # ═══ 主题 ═══
    def _toggle_theme(self, e):
        cur = self.ui.theme_mode_key
        new = "dark" if cur != "dark" else "light"
        self.ui.theme_mode_key = new
        self.ui.save_theme_mode()
        self.page.theme_mode = self.ui.theme_mode()
        e.control.selected = (new == "dark")
        self.page.update()

    # ═══ 滚动 ═══
    def _sync_bottom_btn(self, show: bool):
        """动态插入/移除按钮，避免 visible=False 仍干扰滚轮事件。"""
        if show == self._bottom_btn_visible:
            return
        self._bottom_btn_visible = show
        try:
            ctrls = self._root.controls
            if show and self._to_bottom_btn not in ctrls:
                if self._transport.root in ctrls:
                    idx = ctrls.index(self._transport.root)
                    ctrls.insert(idx, self._to_bottom_btn)
            elif not show and self._to_bottom_btn in ctrls:
                ctrls.remove(self._to_bottom_btn)
            self._push_update()
        except Exception:
            pass

    def _scroll_to_bottom(self):
        try:
            self._near_bottom = True
            self._list_view.auto_scroll = True
            self._sync_bottom_btn(False)
            self._list_view.scroll_to(offset=1_000_000, duration=200)
            self._push_update()
        except Exception:
            pass

    # ═══ EventBus 订阅 ═══
    def _subscribe(self):
        if self._subscribed:
            return
        bus = self.state.bus
        handlers = {
            "msg": self._on_msg,
            "msg_delta": self._on_msg_delta,
            "msg_end": self._on_msg_end,
            "random_event_msg": self._on_random_event,
            "random_npc_msg": self._on_npc,
            "set_status": self._on_set_status,
            "scene_changed": self._on_scene_changed,
            "user_turn": self._on_user_turn,
            "started": lambda d: self._on_loop_event("started", d),
            "paused": lambda d: self._on_loop_event("paused", d),
            "resumed": lambda d: self._on_loop_event("resumed", d),
            "stopped": lambda d: self._on_loop_event("stopped", d),
            "api_error_stop": self._on_api_error,
            "saving": lambda d: self._on_saving(),
            "saved": self._on_saved,
            "autosave_prompt": self._on_autosave_prompt,
        }
        for ev, h in handlers.items():
            bus.on(ev, h)
            self._handlers[ev] = h
        self._subscribed = True

    def _unsubscribe(self):
        bus = self.state.bus
        for ev, h in self._handlers.items():
            try:
                bus.off(ev, h)
            except Exception:
                pass
        self._handlers.clear()
        self._subscribed = False

    # ── 消息处理 ──
    def _on_msg(self, entry):
        if entry.get("streaming"):
            return self._on_streaming_start(entry)
        self._add_entry(entry)

    def _on_streaming_start(self, entry):
        """创建流式空白气泡，存入 _streaming_rows 以便后续更新。"""
        row = make_bubble_row(entry, self.state, self._bubble_max_width())
        self._add_bubble(row)
        mid = entry.get("msg_id", "")
        if mid:
            self._streaming_rows[mid] = row
        self._streaming_count += 1

    def _on_msg_delta(self, entry):
        """流式增量：更新已有气泡的文本内容（无动画）。"""
        mid = entry.get("msg_id", "")
        row = self._streaming_rows.get(mid)
        if row is None:
            return
        was_near = self._near_bottom
        text = entry.get("text", "")
        max_w = self._bubble_max_width()
        new_content = render_streaming_text(text, max_w)
        self._replace_bubble_content(row, new_content)
        if was_near:
            self._near_bottom = True
            self._list_view.auto_scroll = True
            self._sync_bottom_btn(False)
        try:
            self._push_update()
        except Exception:
            pass

    def _on_msg_end(self, entry):
        """流式结束：最终渲染（完整 action 解析），移除追踪。"""
        mid = entry.get("msg_id", "")
        row = self._streaming_rows.pop(mid, None)
        if row is None:
            return
        self._streaming_count = max(0, self._streaming_count - 1)
        was_near = self._near_bottom
        text = entry.get("text", "")
        max_w = self._bubble_max_width()
        new_content = _md(text, max_w)
        self._replace_bubble_content(row, new_content)
        if was_near:
            self._near_bottom = True
            self._list_view.auto_scroll = True
            self._sync_bottom_btn(False)
        else:
            if self._streaming_count == 0:
                self._sync_bottom_btn(not self._near_bottom)
        try:
            self._push_update()
        except Exception:
            pass

    def _replace_bubble_content(self, row: ft.Row, new_content: ft.Control):
        """替换气泡 Row 内部的内容控件。"""
        try:
            inner_col = row.controls[1]  # ft.Column
            bubble_container = inner_col.controls[1]  # ft.Container (bubble)
            bubble_container.content = new_content
        except (IndexError, AttributeError):
            pass

    def _on_random_event(self, entry):
        self._add_entry(entry)

    def _on_npc(self, entry):
        if entry.get("streaming"):
            return self._on_streaming_start(entry)
        self._add_entry(entry)

    def _add_entry(self, entry):
        row = make_bubble_row(entry, self.state, self._bubble_max_width())
        self._add_bubble(row)

    def _add_bubble(self, row: ft.Control):
        row.opacity = 0
        row.offset = ft.Offset(0, 0.04)
        row.animate_opacity = ft.Animation(250, ft.AnimationCurve.EASE_OUT)
        row.animate_offset = ft.Animation(250, ft.AnimationCurve.EASE_OUT)
        self._list_view.controls.append(row)
        if len(self._list_view.controls) > 300:
            del self._list_view.controls[:-300]
        self._has_msgs = True
        self._empty_state.visible = False
        self._push_update()
        row.opacity = 1
        row.offset = ft.Offset(0, 0)
        self._push_update()
        self._update_count()

    def _on_set_status(self, text: str):
        self._update_status(text or "", self.state.running, self.state.paused)

    def _on_scene_changed(self, scene: dict):
        # 场景横幅 + 内联分割行 + 更新 header
        if scene:
            self._scene_banner.show(scene)
            if not scene.get("manual"):
                row = make_scene_change_row(scene, self._bubble_max_width())
                self._add_bubble(row)
        self._refresh_header_menu()

    def _on_user_turn(self, _data):
        self._user_turn = True
        self._transport.set_running(True, True)
        self._update_status("轮到你了～", self.state.running, True)
        self._director_input.refresh(self.state.director_mode, self.state.user_mode, True)

    def _on_loop_event(self, kind, _data):
        if kind == "started":
            self._transport.set_running(True, False)
            self._update_status("运行中", True, False)
        elif kind == "paused":
            self._transport.set_running(True, True)
            self._update_status("已暂停", True, True)
        elif kind == "resumed":
            self._user_turn = False
            self._transport.set_running(True, False)
            self._update_status("运行中", True, False)
            self._director_input.refresh(self.state.director_mode, self.state.user_mode, False)
        elif kind == "stopped":
            self._user_turn = False
            self._saving = False
            self._transport.set_running(False, False)
            self._update_status("已停止", False, False)
            self._director_input.hide()
            self._reset_to_empty()

    def _on_api_error(self, msg: str):
        # stop() 会 emit "stopped" 事件，由 _on_loop_event 处理 UI 重置
        # 这里只弹出错误提示对话框
        dlg = ft.AlertDialog(
            title=ft.Text("API 错误"),
            content=ft.Text(msg or "连续失败，对话已停止"),
            actions=[ft.TextButton("知道了", on_click=lambda e: self._close_dialog())],
        )
        try:
            self.page.show_dialog(dlg)
        except Exception:
            pass

    def _on_saving(self):
        self._update_status("正在保存…", self.state.running, self.state.paused)
        if self._save_dialog:
            self._save_dialog.set_step(1, "正在生成对话标题…", delay=0.1)

    def _on_saved(self, data: dict):
        self._saving = False
        ok = data.get("success", False) if isinstance(data, dict) else False
        msg = data.get("message", "保存成功" if ok else "保存失败") if isinstance(data, dict) else "保存完成"
        title = data.get("title", "") if isinstance(data, dict) else ""
        had_dialog = self._save_dialog is not None
        if self._save_dialog:
            if ok:
                summary = f"保存成功：{title}" if title else "保存成功"
                self._save_dialog.set_step(2, "完成", delay=0.1)
                self._save_dialog.complete(summary)
            else:
                self._save_dialog.fail(msg)
            self._save_dialog = None
        # 若没有进度对话框（如外部调用保存），用 SnackBar 兜底
        if not had_dialog:
            self._snack(msg)
        self._update_status(msg, self.state.running, self.state.paused)

    def _on_autosave_prompt(self, data: dict):
        title = data.get("title", "未命名") if isinstance(data, dict) else "未命名"
        count = data.get("message_count", 0) if isinstance(data, dict) else 0
        path = data.get("path", "") if isinstance(data, dict) else ""

        def restore(e=None):
            try:
                if self.state.loop.running:
                    self.state.loop.stop()
                if path:
                    self.state.chat.restore_autosave(path)
            except Exception as ex:
                print(f"[chat] 恢复自动存档失败: {ex}")
            self._close_dialog()
            self._reload_history_into_list()
            self._refresh_header_menu()

        def discard(e=None):
            try:
                if path:
                    self.state.chat.discard_autosave(path)
            except Exception:
                pass
            self._close_dialog()

        dlg = ft.AlertDialog(
            title=ft.Text("恢复对话"),
            content=ft.Text(f"检测到上次未保存的对话「{title}」{count} 条消息，是否恢复？"),
            actions=[
                ft.FilledButton("恢复", on_click=restore),
                ft.TextButton("放弃", on_click=discard),
            ],
        )
        try:
            self.page.show_dialog(dlg)
        except Exception:
            pass

    def _reload_history_into_list(self):
        """把 state.history 重灌进气泡列表。"""
        self._list_view.controls.clear()
        for entry in self.state.history_snapshot():
            row = make_bubble_row(entry, self.state, self._bubble_max_width())
            row.opacity = 1
            row.offset = ft.Offset(0, 0)
            self._list_view.controls.append(row)
        self._has_msgs = bool(self.state.history)
        self._empty_state.visible = not self._has_msgs
        try:
            self.page.update()
        except Exception:
            pass
        if self._has_msgs:
            self._scroll_to_bottom()
        self._update_count()

    # ═══ 生命周期 ═══
    def on_enter(self):
        from core.debug import trace, check_bus_leaks
        trace("chat_view.on_enter")
        if not self._built:
            return
        # 如果在剧本编辑页加载了其他剧本，恢复活跃剧本数据
        active = config.app_config.get("active_profile", "")
        if active and self.state.profile_dir:
            current_folder = self.state.profile_dir.name
            if current_folder != active:
                saved_scene_idx = self.state.scene_idx
                saved_current_scene = self.state.current_scene
                saved_scene_version = self.state.scene_version
                saved_last_scene_update_turn = self.state._last_scene_update_turn
                self.state.data.load_profile(active)
                self.state.scene_idx = saved_scene_idx
                self.state.current_scene = saved_current_scene
                self.state.scene_version = saved_scene_version
                self.state._last_scene_update_turn = saved_last_scene_update_turn
        self._subscribe()
        check_bus_leaks(self.state.bus, expected_event_count=len(self._handlers))
        self._refresh_header_menu()
        self._mode_chips.refresh()
        self._transport.refresh()
        # _dirty 标记：离开 chat 后可能错过事件 / 切换了剧本 / 读取了存档
        # 重新进入时需要同步视觉列表与 state.history
        if self._dirty:
            self._dirty = False
            if not self.state.history:
                self._reset_to_empty()
            else:
                self._reload_history_into_list()
        self._update_status(
            "已暂停" if self.state.running and self.state.paused
            else ("运行中" if self.state.running else "就绪"),
            self.state.running, self.state.paused
        )
        self._update_count()
        # 提示角色加载错误
        errors = getattr(self.state, '_char_load_errors', None) or []
        if errors:
            self._snack(f"部分角色文件加载失败: {', '.join(errors)}")
            self.state._char_load_errors = []

    def on_leave(self):
        from core.debug import trace, check_bus_leaks
        trace("chat_view.on_leave")
        # 离开聊天页时暂停对话（避免在别的页面继续消耗 API）
        if self.state.loop.running and not self.state.loop.paused:
            self.state.loop.pause()
        # 取消场景横幅定时器，避免离开后幽灵淡出
        self._scene_banner.cancel()
        # 标记为 dirty：返回时需重新同步
        self._dirty = True
        self._unsubscribe()
        check_bus_leaks(self.state.bus)
        # 若保存进度对话框仍打开，关闭它（避免悬挂）
        if self._save_dialog:
            self._save_dialog.close()
            self._save_dialog = None
            self._saving = False

    # ═══ 状态更新（Step 4 EventBus 调用）═══
    def _update_status(self, text: str, running: bool, paused: bool):
        if self._status_text:
            self._status_text.value = text
        if self._status_dot:
            if running and not paused:
                self._status_dot.bgcolor = ft.Colors.TERTIARY  # 青绿 运行
            elif paused:
                self._status_dot.bgcolor = ft.Colors.SECONDARY  # 琥珀 暂停
            else:
                self._status_dot.bgcolor = ft.Colors.OUTLINE
        self._push_update()

    def _update_count(self):
        if self._count_text:
            self._count_text.value = f"{self.state.message_count} 条"
            self._push_update()
