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
        self._list_view: ft.Column = None  # 滚动容器（Column with scroll, 不是 ListView）
        self._built = False
        self._subscribed = False
        self._dirty = True  # 首次进入需初始化；离开后需重新同步
        self._handlers = {}
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
        self._bottom_btn_visible = False  # 按钮是否可见（Stack overlay，切换 visible 不影响布局）
        self._user_scrolled = False  # 用户主动上滚后置 True；新消息不自动跟随
        self._near_bottom = True  # 当前滚动位置是否接近底部
        self._last_pixels = 0.0  # 上一次 on_scroll 的 pixels 值，用于方向检测
        self._user_scroll_time = 0.0  # 上一次用户主动上滚的时间戳，防止程序滚动覆盖用户意图
        self._last_add_time = 0.0  # 上一次 _add_bubble 的时间戳，防止列表变化导致的滚动重置被误判为用户上滚
        self._delta_update_timer = None  # delta update + scroll 节流定时器（100ms，Web WebSocket 友好）
        self._scroll_timer = None  # 延迟 scroll_to 定时器（等布局稳定后再滚动）
        self._last_history_count = -1  # 上次渲染的 history 条目数，用于跳过不必要的重建

    # ═══ 构建视图 ═══
    def build(self) -> ft.Control:
        self._mode_chips = ModeChips(self.page, self.state, on_change=self._on_mode_change)

        # 状态指示器（合并到 TransportBar 中）
        self._status_dot = ft.Container(
            width=8, height=8, border_radius=4,
            bgcolor=ft.Colors.OUTLINE,
        )
        self._status_text = ft.Text("就绪", size=12, color=ft.Colors.ON_SURFACE_VARIANT,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
        self._count_text = ft.Text("0 条", size=12, color=ft.Colors.ON_SURFACE_VARIANT,
                                   max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)

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
                        on_click=lambda e: self._scroll_to_bottom(delay=0, animated=True),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                            shape=ft.CircleBorder(),
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.Padding.only(bottom=8, top=4),
            bottom=12,
            right=12,
            visible=False,
            ignore_interactions=False,
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
            expand=True,
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
            content=ft.Row([self._scene_text], spacing=4, tight=True),
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
                    ft.Container(content=title_btn, expand=True),
                    scene_btn,
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

    # ── 内容区（空状态 + 气泡列表 + banner slot + 回到底部按钮 overlay）──
    def _build_content(self) -> ft.Control:
        self._empty_state = self._build_empty_state()
        # 用 Column(scroll=ScrollMode.AUTO) 代替 ListView：
        # - ListView 的 scroll_to 对动态构建的控件无效（Flet 官方文档明确说明）
        # - Column 构建所有子控件，scroll_to 可正常工作
        # - auto_scroll=False 固定：scroll_to 要求 auto_scroll=False 才能工作
        #   切换 auto_scroll 会导致 Flutter 重置滚动位置为 0（顶部），故保持 False
        #   新消息的手动滚动由 _add_bubble 调用 _scroll_to_bottom 处理
        self._list_view = ft.Column(
            controls=[],
            expand=True,
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            auto_scroll=False,
            on_scroll=self._on_scroll,
        )
        # Column 无 padding 属性，用 Container 包裹提供内边距
        list_container = ft.Container(
            content=self._list_view,
            expand=True,
            padding=ft.Padding.symmetric(horizontal=8, vertical=8),
        )
        # Stack overlay：按钮通过 bottom/right 定位悬浮于右下角，切换 visible 不影响布局
        self._content_stack = ft.Stack(
            controls=[list_container, self._empty_state, self._scene_banner.root, self._to_bottom_btn],
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
        """滚动事件处理。

        核心策略（跨平台 Windows/macOS/Android/Web）：
        1. 永不修改 auto_scroll 属性 —— auto_scroll=False 固定，scroll_to 可正常工作。
        2. 本方法仅跟踪用户滚动状态用于按钮可见性，不干预滚动行为。
        3. 方向检测：pixels 减小 = 用户上滚 → 显示"回到底部"按钮。
        4. 时间窗口保护：_add_bubble 后 300ms 内跳过方向检测
           （列表变化可能触发 pixels=0 的重置事件，不应误判为用户上滚）。
        """
        import time
        try:
            pixels = float(getattr(e, "pixels", 0) or 0)
            max_ext = float(getattr(e, "max_scroll_extent", 0) or 0)
            near_bottom = (max_ext - pixels) < 120

            prev_pixels = self._last_pixels
            self._last_pixels = pixels
            now = time.time()

            # 时间窗口：_add_bubble 后 300ms 内跳过方向检测
            recently_added = (now - self._last_add_time) < 0.30

            # 方向检测：pixels 明显减小 → 用户上滚（5px 阈值过滤触摸抖动）
            if not recently_added and not near_bottom and prev_pixels > pixels + 5:
                self._user_scrolled = True
                self._user_scroll_time = now

            # 回到底部时清除 _user_scrolled
            if near_bottom and (now - self._user_scroll_time) > 0.35:
                self._user_scrolled = False

            self._near_bottom = near_bottom
            # 按钮可见性：用户已上滚且有消息时显示
            self._sync_bottom_btn(self._user_scrolled and self._has_msgs)
        except Exception:
            pass

    def _build_empty_state(self) -> ft.Control:
        folder = config.app_config.get("active_profile", "")
        emoji = profile_emoji(folder, self.state.title)
        title = ft.Text(self.state.title, size=22, weight=ft.FontWeight.W_700,
                        text_align=ft.TextAlign.CENTER, max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS)
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
        self._last_history_count = 0
        self._reset_streaming_state()
        self._empty_state.visible = True
        self._rebuild_empty_state()
        self._update_status("就绪", False, False)
        if self._count_text:
            self._count_text.value = "0 条"
        try:
            self.page.update()
        except Exception:
            pass

    def _reset_streaming_state(self):
        """清理流式追踪状态 + 滚动相关状态。

        stop/导航离开后 msg_end 可能因取消订阅而丢失，导致 _streaming_count 卡死、
        _streaming_rows 残留 stale row。本方法在所有重置/重载入口调用，确保按钮逻辑不被卡死。
        """
        self._streaming_rows.clear()
        self._streaming_count = 0
        self._user_scrolled = False
        self._near_bottom = True
        self._last_pixels = 0.0
        self._user_scroll_time = 0.0
        self._last_add_time = 0.0
        if self._delta_update_timer is not None:
            self._delta_update_timer.cancel()
            self._delta_update_timer = None
        if self._scroll_timer is not None:
            self._scroll_timer.cancel()
            self._scroll_timer = None
        # 重置按钮可见性状态，强制 _sync_bottom_btn 重新评估
        self._bottom_btn_visible = True  # 强制下次 _sync_bottom_btn(False) 触发 visible 切换
        self._sync_bottom_btn(False)

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
            # 用户回合时 resume() 不会 emit "resumed"（loop 检测到 _waiting_for_user + You 在顺序中），
            # transport_bar 按钮状态不变，用户无感知。加 snack 明确提示。
            if (self.state.loop._waiting_for_user
                    and "You" in self.state.loop.app._get_effective_order()):
                self._snack("请先输入发言或跳过")
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
        """切换回到底部按钮的可见性。

        按钮作为 Stack overlay（bottom-right 定位），切换 visible 不影响 ListView 布局。
        此前动态插入/移除按钮到 root Column 会在 Android 上触发 Column 重新布局，
        导致 ListView 丢失滚动位置（回到顶部）。
        """
        if show == self._bottom_btn_visible:
            return
        self._bottom_btn_visible = show
        try:
            self._to_bottom_btn.visible = show
            self._push_update()
        except Exception:
            pass

    def _scroll_to_bottom(self, delay=0.05, animated=True):
        """手动滚动到列表底部。

        使用场景：
        - "回到底部"按钮点击（animated=True，平滑动画）
        - _reload_history_into_list 初始加载（animated=False，瞬间跳转）
        - _add_bubble 新消息到达（animated=False，仅当用户在底部附近时）

        实现要点：
        - auto_scroll=False 固定，scroll_to 可正常工作
        - offset=-1 表示跳到末尾（Flet API：负值相对于末尾）
        - delay 确保 Column 布局完成后再滚动（布局异步，立即调用可能 max_extent=0）
        - 用户在 delay 期间上滚则取消滚动
        """
        self._user_scrolled = False
        self._near_bottom = True
        self._sync_bottom_btn(False)

        import threading

        # 取消待执行的 scroll
        if self._scroll_timer is not None:
            self._scroll_timer.cancel()
            self._scroll_timer = None

        duration = 200 if animated else 0

        def _do_scroll():
            self._scroll_timer = None
            if self._user_scrolled:
                return  # 用户在 delay 期间上滚 → 取消
            try:
                # offset=-1：跳到末尾（Flet API：负值相对于末尾）
                coro = self._list_view.scroll_to(offset=-1, duration=duration)
                self._schedule_coro(coro)
            except Exception:
                pass

        if delay > 0:
            t = threading.Timer(delay, _do_scroll)
            t.daemon = True
            self._scroll_timer = t
            t.start()
        else:
            _do_scroll()

    def _schedule_coro(self, coro):
        """将 coroutine 安全调度到 async loop。

        - Web 模式（有 async loop）：run_coroutine_threadsafe 到现有 loop
        - 移动端/桌面原生（无 async loop）：在新线程中 asyncio.run(coro)
          scroll_to() 内部通过 _invoke_method 发送命令到 Flutter，
          命令发送是线程安全的，无需依赖特定 event loop
        """
        if coro is None:
            return
        try:
            import asyncio
            if not asyncio.iscoroutine(coro):
                return
            loop = self._async_loop
            if loop is not None and loop.is_running():
                asyncio.run_coroutine_threadsafe(coro, loop)
            else:
                # 无运行中的 async loop（移动端/桌面原生）
                # 在新线程中运行协程，确保 scroll 命令发出
                import threading
                def _run():
                    try:
                        asyncio.run(coro)
                    except Exception:
                        pass
                t = threading.Thread(target=_run, daemon=True)
                t.start()
        except Exception:
            try:
                coro.close()
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
        self._add_bubble(row, fade_in=False, is_message=True)  # 流式气泡不渐入，避免空白
        mid = entry.get("msg_id", "")
        if mid:
            self._streaming_rows[mid] = row
            self._streaming_count += 1
        # msg_id 为空时不计入 _streaming_count，避免 _on_msg_end 因 row is None 提前 return 而漏减

    def _on_msg_delta(self, entry):
        """流式增量：更新已有气泡的文本内容（无动画）。"""
        mid = entry.get("msg_id", "")
        row = self._streaming_rows.get(mid)
        if row is None:
            return
        text = entry.get("text", "")
        max_w = self._bubble_max_width()
        new_content = render_streaming_text(text, max_w)
        self._replace_bubble_content(row, new_content)
        # 节流：合并 100ms 内的多次 delta 为一次 scroll_to + page.update()
        # auto_scroll=False，需手动滚动跟随流式输出
        self._schedule_delta_flush()

    def _schedule_delta_flush(self):
        """合并 100ms 内的多次 delta 为一次 scroll_to + page.update()。

        - 用户未上滚 → scroll_to(offset=-1) 跟随流式输出到底部
        - 用户已上滚 → 仅 update，不滚动（用户可自由阅读历史）
        """
        if self._delta_update_timer is not None:
            return  # 已有待触发的 flush
        import threading

        def _flush():
            self._delta_update_timer = None
            try:
                if not self._user_scrolled:
                    self._scroll_to_bottom(delay=0, animated=False)
                self._push_update()
            except Exception:
                pass

        t = threading.Timer(0.1, _flush)
        t.daemon = True
        self._delta_update_timer = t
        t.start()

    def _on_msg_end(self, entry):
        """流式结束：最终渲染（完整 action 解析），移除追踪。"""
        mid = entry.get("msg_id", "")
        row = self._streaming_rows.pop(mid, None)
        if row is None:
            # row is None：此 msg_id 未被 _on_streaming_start 追踪（可能是空 msg_id 跳过追踪，
            # 或 msg_end 重复 emit，或导航离开后残留事件）。不递减 _streaming_count 以防错减别人的计数。
            # 仍走 _finalize_msg_end 取消挂起定时器（若有）。
            self._finalize_msg_end(entry)
            return
        self._streaming_count = max(0, self._streaming_count - 1)
        text = entry.get("text", "")
        max_w = self._bubble_max_width()
        new_content = _md(text, max_w)
        self._replace_bubble_content(row, new_content)
        self._finalize_msg_end(entry)

    def _finalize_msg_end(self, entry):
        """msg_end 共用收尾：取消挂起的 delta flush 定时器，立即 scroll + push 最终内容。"""
        if self._delta_update_timer is not None:
            self._delta_update_timer.cancel()
            self._delta_update_timer = None
        try:
            if not self._user_scrolled:
                # 流式消息完成 → 滚动到底部显示最终内容
                self._scroll_to_bottom(delay=0, animated=False)
            else:
                # 用户已上滚 → 确保按钮显示
                self._sync_bottom_btn(True)
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
        self._add_bubble(row, fade_in=not entry.get("streaming"), is_message=True)

    def _add_bubble(self, row: ft.Control, fade_in: bool = True, is_message: bool = True):
        import time
        self._last_add_time = time.time()  # 标记添加时间，_on_scroll 据此跳过方向检测窗口
        if is_message:
            self._last_history_count += 1  # 跟踪已渲染的 history 条目数
        if fade_in:
            # 非流式消息：渐入动画（opacity 0→1 + 轻微上移）
            row.opacity = 0
            row.offset = ft.Offset(0, 0.04)
            row.animate_opacity = ft.Animation(250, ft.AnimationCurve.EASE_OUT)
            row.animate_offset = ft.Animation(250, ft.AnimationCurve.EASE_OUT)
        # 流式消息：不设 opacity=0，避免空白气泡
        self._list_view.controls.append(row)
        if len(self._list_view.controls) > 300:
            del self._list_view.controls[:-300]
        self._has_msgs = True
        self._empty_state.visible = False
        self._push_update()
        if fade_in:
            row.opacity = 1
            row.offset = ft.Offset(0, 0)
            self._push_update()
        self._update_count()
        # auto_scroll=False，需手动滚动到底部
        # 用户未上滚 → 滚到底部跟随新消息；用户已上滚 → 显示按钮
        if not self._user_scrolled:
            self._scroll_to_bottom(delay=0.05, animated=False)
        else:
            self._sync_bottom_btn(True)

    def _on_set_status(self, text: str):
        self._update_status(text or "", self.state.running, self.state.paused)

    def _on_scene_changed(self, scene: dict):
        # 场景横幅 + 内联分割行 + 更新 header
        if scene:
            self._scene_banner.show(scene)
            if not scene.get("manual"):
                row = make_scene_change_row(scene, self._bubble_max_width())
                self._add_bubble(row, is_message=False)  # 场景变更行不在 history 中
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
        import time
        snapshot = self.state.history_snapshot()
        current_count = len(snapshot)

        # 如果 history 条目数未变，跳过重建 —— 避免切 tab 回来时 ListView 被清空重建
        # 导致滚动位置重置（消息从顶部滑到底部）。
        # on_leave 暂停了 loop，离开期间不会有新消息，count 不变即内容不变。
        if current_count > 0 and current_count == self._last_history_count and self._has_msgs:
            # 列表已是最新，只需确保滚动位置正确
            self._scroll_to_bottom(delay=0.05, animated=False)
            return

        self._last_history_count = current_count
        self._list_view.controls.clear()
        # 清理流式追踪状态：on_enter 重载时若有未完成的流式消息（msg_end 在取消订阅期间丢失），
        # _streaming_rows 会残留 stale row 且 _streaming_count 卡死，导致回到底部按钮永久失效
        self._reset_streaming_state()
        # 标记加载时间（在 _reset_streaming_state 之后，否则会被重置为 0）
        # 防止初始滚动事件被误判为用户上滚
        self._last_add_time = time.time()
        for entry in snapshot:
            row = make_bubble_row(entry, self.state, self._bubble_max_width())
            row.opacity = 1
            row.offset = ft.Offset(0, 0)
            self._list_view.controls.append(row)
        self._has_msgs = bool(snapshot)
        self._empty_state.visible = not self._has_msgs
        try:
            self.page.update()
        except Exception:
            pass
        if self._has_msgs:
            # auto_scroll=False，需手动 scroll_to(offset=-1) 滚到底部
            # delay=0.15 等 Column 布局完成（布局异步，立即调用可能 max_extent=0）
            self._scroll_to_bottom(delay=0.15, animated=False)
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
                # 剧本切换后 history 完全变化，强制重建列表
                self._last_history_count = -1
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
        # 取消流式 delta flush 定时器 + 延迟 scroll 定时器，避免离开后冗余 page.update()/scroll_to
        # 同时清理流式追踪状态，防止 msg_end 在取消订阅期间丢失导致 _streaming_count 卡死
        self._reset_streaming_state()
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
