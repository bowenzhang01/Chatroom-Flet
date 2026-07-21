# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · 剧本库视图
  AppBar: 剧本库 + + 新建 + ✨ AI 创建
  卡片网格（手机2列 / 桌面3-4列）：封面渐变 + emoji + 信息
  菜单：重命名/复制/删除/导出
  点卡片 → 进入剧本详情（Step 6b）
"""

import shutil

import flet as ft

import config
from app.views import ViewBase
from app.theme import RADIUS_CARD, TEXT_XL, TEXT_SM, TEXT_ML, TEXT_MD, TEXT_XS
from app.components.profile_card import ProfileCard, gather_profile_meta
from app.components.progress_dialog import ProgressDialog

__all__ = ["ProfilesView"]


class ProfilesView(ViewBase):
    def __init__(self, page, app_state, ui_state, router):
        super().__init__(page, app_state, ui_state, router)
        self._body: ft.Container = None
        self._detail_folder: str = None
        self._detail_section: int = 0
        self._detail_body: ft.Container = None
        self._turn_editor = None
        self._built = False
        # 保存订阅生命周期管理（save_and_switch 用）
        self._save_dialog: ProgressDialog = None
        self._save_switch_folder: str = None  # 保存完成后要切换的目标剧本
        self._save_switch_done = False
        self._save_timeout_done = False
        self._save_generation = 0  # 保存代际令牌：隔离旧超时线程
        self._opened_sheet: ft.BottomSheet = None

    def build(self) -> ft.Control:
        self._body = ft.Container(expand=True, padding=ft.Padding.all(16))
        self._root = ft.Column(
            controls=[self._build_header(), self._body],
            spacing=0,
            expand=True,
        )
        self._built = True
        self._render()
        return self._root

    # ── Header ──
    def _build_header(self) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("剧本库", size=TEXT_XL, weight=ft.FontWeight.W_700),
                    ft.Container(expand=True),
                    ft.FilledTonalButton(
                        content=ft.Text("新建"), icon=ft.Icons.ADD,
                        on_click=lambda e: self._new_profile_dialog(),
                    ),
                    ft.FilledButton(
                        content=ft.Text("AI 创建"), icon=ft.Icons.AUTO_AWESOME,
                        on_click=lambda e: self._ai_create_dialog(),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    # ── 渲染网格 / 详情 ──
    def _render(self):
        if self._detail_folder:
            self._body.content = self._build_detail(self._detail_folder)
        else:
            self._body.content = self._build_grid()
        try:
            self.page.update()
        except Exception:
            pass

    def _build_grid(self) -> ft.Control:
        profiles = self.state.data.get_profile_list()
        metas = [gather_profile_meta(p) for p in profiles]
        cards = []
        for m in metas:
            card = ProfileCard(
                self.page, m,
                on_open=self._open_detail,
                on_menu=self._on_card_menu,
            )
            cards.append(ft.Column(
                controls=[card.root],
                col={"xs": 6, "sm": 6, "md": 4, "lg": 3},
            ))
        if not cards:
            return ft.Container(
                content=ft.Text("暂无剧本，点击「新建」或「✨ AI 创建」开始",
                                size=TEXT_SM, color=ft.Colors.ON_SURFACE_VARIANT),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        return ft.Column(
            controls=[ft.ResponsiveRow(controls=cards, spacing=12, run_spacing=12)],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    # ── 详情（4 分区）──
    def _build_detail(self, folder: str) -> ft.Control:
        meta = gather_profile_meta(folder)
        self._detail_section = 0
        self._detail_body = ft.Container(expand=True, padding=ft.Padding.all(16))
        seg = ft.SegmentedButton(
            selected=[0],
            segments=[
                ft.Segment(value=i, label=ft.Text(l, size=TEXT_SM))
                for i, l in enumerate(["概览", "场景", "角色", "发言"])
            ],
            allow_multiple_selection=False,
            allow_empty_selection=False,
            on_change=self._on_section_change,
        )
        self._render_detail_body()
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.TextButton(content=ft.Text("← 返回"),
                                          on_click=lambda e: self._back_to_list()),
                            ft.Text(meta["title"], size=TEXT_XL, weight=ft.FontWeight.W_700,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                            ft.FilledButton(content=ft.Text("进入对话"), icon=ft.Icons.PLAY_ARROW,
                                            on_click=lambda e: self._enter_chat(folder)),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                ),
                ft.Container(content=seg, padding=ft.Padding.symmetric(horizontal=16)),
                self._detail_body,
            ],
            spacing=0,
            expand=True,
        )

    def _on_section_change(self, e):
        sel = e.control.selected
        self._detail_section = int(next(iter(sel), 0))
        self._render_detail_body()

    def _render_detail_body(self):
        idx = self._detail_section
        if idx == 0:
            self._detail_body.content = self._section_overview()
        elif idx == 1:
            self._detail_body.content = self._section_scenes()
        elif idx == 2:
            self._detail_body.content = self._section_characters()
        elif idx == 3:
            self._detail_body.content = self._section_turn()
        try:
            self._detail_body.update()
            self._body.update()
            self.page.update()
        except Exception:
            pass

    # ── 概览 ──
    def _section_overview(self) -> ft.Control:
        world = self.state._profile_config.get("world", {}).get("setting", "")
        title_f = ft.TextField(label="应用标题", value=self.state.title, dense=True)
        world_f = ft.TextField(label="世界观", value=world, multiline=True, min_lines=3, max_lines=5)

        def _save(e=None):
            self.state.title = title_f.value or self.state.title
            self.state._profile_config.setdefault("app", {})["title"] = title_f.value or self.state.title
            self.state._profile_config.setdefault("world", {})["setting"] = world_f.value or ""
            try:
                self.state.data._save_profile_config()
            except Exception:
                pass
            self._snack("已保存")

        def _ai_infer(e=None):
            if not config.API_KEY:
                self._snack("请先在设置中配置 API Key")
                return
            dlg = ProgressDialog(self.page, title="✨ AI 推断世界观")
            dlg.show(status="正在分析剧本信息…", indeterminate=True)

            def _on_result(world):
                if world:
                    self.state._profile_config.setdefault("world", {})["setting"] = world
                    try:
                        self.state.data._save_profile_config()
                    except Exception:
                        pass
                    dlg.complete("已推断世界观", on_close=self._render_detail_body)
                else:
                    dlg.fail("未能生成世界观")

            def _on_error(msg):
                dlg.fail("推断失败：" + str(msg)[:60])

            try:
                self.state.ai.infer_world_async(_on_result, _on_error)
            except Exception as ex:
                dlg.fail("推断失败：" + str(ex)[:60])

        return ft.Column(
            controls=[
                ft.Text("剧本信息", size=TEXT_MD, weight=ft.FontWeight.W_600),
                title_f,
                world_f,
                ft.Row(
                    controls=[
                        ft.FilledButton(content=ft.Text("保存"), icon=ft.Icons.SAVE, on_click=_save),
                        ft.OutlinedButton(content=ft.Text("AI 推断"), icon=ft.Icons.AUTO_AWESOME, on_click=_ai_infer),
                    ],
                    spacing=8,
                ),
                ft.Container(height=8),
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    # ── 场景 ──
    def _section_scenes(self) -> ft.Control:
        scenes = self.state.scenes or []
        rows = []
        for i, sc in enumerate(scenes):
            rows.append(ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DRAG_HANDLE, size=18, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Column(
                            controls=[
                                ft.Text(f"{sc.get('time','')} · {sc.get('location','')}", size=TEXT_SM,
                                        weight=ft.FontWeight.W_500, max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(sc.get("scene", ""), size=TEXT_XS, color=ft.Colors.ON_SURFACE_VARIANT,
                                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                            spacing=0, tight=True, expand=True,
                        ),
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT,
                            items=[
                                ft.PopupMenuItem(content=ft.Text("编辑"), icon=ft.Icons.EDIT,
                                                 on_click=lambda e, idx=i: self._edit_scene(idx)),
                                ft.PopupMenuItem(content=ft.Text("删除"), icon=ft.Icons.DELETE_OUTLINE,
                                                 on_click=lambda e, idx=i: self._delete_scene(idx)),
                            ],
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                border_radius=8,
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            ))
        header = ft.Row(
            controls=[
                ft.FilledTonalButton(content=ft.Text("添加场景"), icon=ft.Icons.ADD, on_click=lambda e: self._edit_scene(None)),
                ft.OutlinedButton(content=ft.Text("AI 生成"), icon=ft.Icons.AUTO_AWESOME,
                                  on_click=lambda e: self._ai_generate_scenes()),
            ],
            spacing=8,
        )
        return ft.Column(
            controls=[header, ft.Container(height=8)] + rows,
            spacing=6,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    # ── 角色 ──
    def _section_characters(self) -> ft.Control:
        from app.components.character_card import CharacterCard, AddCharacterCard, AIGenerateCharacterCard
        chars = [(n, c) for n, c in self.state.characters.items()]
        total = max(1, len(chars))
        cards = []
        for i, (n, c) in enumerate(chars):
            cc = CharacterCard(
                self.page, c, i, total,
                on_edit=self._edit_character,
                on_ai=self._ai_complete_character,
                on_menu=self._on_char_menu,
            )
            cards.append(ft.Column(controls=[cc.root], col={"xs": 6, "sm": 6, "md": 4, "lg": 3}))
        add_card = AddCharacterCard(self.page, on_add=lambda: self._edit_character(None))
        ai_card = AIGenerateCharacterCard(self.page, on_generate=self._ai_generate_characters)
        cards.append(ft.Column(controls=[add_card.root], col={"xs": 6, "sm": 6, "md": 4, "lg": 3}))
        cards.append(ft.Column(controls=[ai_card.root], col={"xs": 6, "sm": 6, "md": 4, "lg": 3}))
        return ft.Column(
            controls=[ft.ResponsiveRow(controls=cards, spacing=12, run_spacing=12)],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    # ── 发言 ──
    def _section_turn(self) -> ft.Control:
        from app.components.reorderable_list import TurnOrderEditor
        self._turn_editor = TurnOrderEditor(self.page, self.state)
        self._turn_editor.refresh()
        return ft.Column(
            controls=[self._turn_editor.root],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    # ── AI 生成场景 ──
    def _ai_generate_scenes(self):
        if not config.API_KEY:
            self._snack("请先在设置中配置 API Key")
            return
        dlg = ProgressDialog(self.page, title="✨ AI 生成场景")
        dlg.show(
            status="正在生成场景…",
            steps=["分析剧本与角色", "生成场景", "写入剧本"],
            indeterminate=True,
        )
        dlg.set_step(0, "正在分析剧本与角色…")

        def _on_result(scenes):
            if not scenes:
                dlg.fail("未能生成场景")
                return
            dlg.set_step(1, "正在写入剧本…", delay=0.1)
            try:
                for sc in scenes:
                    if isinstance(sc, dict) and sc.get("time"):
                        self.state.scenes.append(sc)
                self.state.data._save_scenes()
                n = len(scenes)
                dlg.complete(f"已生成 {n} 个场景", on_close=self._render_detail_body)
            except Exception as ex:
                dlg.fail("写入失败：" + str(ex)[:60])

        def _on_error(msg):
            dlg.fail("生成失败：" + str(msg)[:60])

        try:
            self.state.ai.generate_scenes_async(_on_result, _on_error)
        except Exception as ex:
            dlg.fail("生成失败：" + str(ex)[:60])

    # ── AI 生成角色 ──
    def _ai_generate_characters(self):
        if not config.API_KEY:
            self._snack("请先在设置中配置 API Key")
            return
        dlg = ProgressDialog(self.page, title="✨ AI 生成角色")
        dlg.show(
            status="正在生成角色…",
            steps=["分析剧本与场景", "生成角色", "写入剧本"],
            indeterminate=True,
        )
        dlg.set_step(0, "正在分析剧本与场景…")

        def _on_result(chars):
            if not chars:
                dlg.fail("未能生成角色")
                return
            dlg.set_step(1, "正在写入剧本…", delay=0.1)
            try:
                added = 0
                for c in chars:
                    if not isinstance(c, dict):
                        continue
                    name = c.get("name", "")
                    if not name or name in self.state.characters:
                        continue
                    c.setdefault("color", "#888888")
                    c.setdefault("bg_color", "#f5f5f5")
                    self.state.data._save_character(name + ".json", c)
                    # 加入发言顺序
                    if name not in self.state.turn_order:
                        self.state.turn_order.append(name)
                    added += 1
                self.state.data._save_turn_order()
                self.state.data._reload_data()
                dlg.complete(f"已生成 {added} 个角色", on_close=self._render_detail_body)
            except Exception as ex:
                dlg.fail("写入失败：" + str(ex)[:60])

        def _on_error(msg):
            dlg.fail("生成失败：" + str(msg)[:60])

        try:
            self.state.ai.generate_characters_async(_on_result, _on_error)
        except Exception as ex:
            dlg.fail("生成失败：" + str(ex)[:60])

    # ── AI 补全角色 ──
    def _ai_complete_character(self, name):
        if not config.API_KEY:
            self._snack("请先在设置中配置 API Key")
            return
        dname = self.state.characters.get(name, {}).get("display_name", name)
        dlg = ProgressDialog(self.page, title=f"✨ 补全 {dname}")
        dlg.show(
            status="正在补全角色设定…",
            steps=["分析现有信息", "生成补全内容", "保存角色"],
            indeterminate=True,
        )
        dlg.set_step(0, "正在分析现有信息…")

        def _on_result(data):
            if not data:
                dlg.fail("未能生成补全内容")
                return
            dlg.set_step(1, "正在保存角色…", delay=0.1)
            try:
                # 合并：保留原字段，用 AI 结果填充缺失项
                original = self.state.characters.get(name, {})
                merged = dict(original)
                for k in ("name", "display_name", "color", "description",
                          "personality", "system_prompt"):
                    if data.get(k):
                        merged[k] = data[k]
                merged.setdefault("bg_color", original.get("bg_color", "#f5f5f5"))
                fname = (merged.get("name") or name) + ".json"
                self.state.data._save_character(fname, merged)
                # 如果改名了，删除旧文件
                new_name = merged.get("name", name)
                if new_name != name:
                    # 迁移 history 中的旧角色名引用
                    # 仅当当前编辑的剧本是活跃剧本时才迁移内存 history；
                    # load_profile_for_edit 不交换 history，非活跃剧本的改名不应碰活跃剧本的 history
                    active_folder = config.app_config.get("active_profile", "")
                    editing_folder = self.state.profile_dir.name if self.state.profile_dir else ""
                    if editing_folder == active_folder:
                        with self.state._history_lock:
                            for entry in self.state.history:
                                if entry.get("name") == name:
                                    entry["name"] = new_name
                    # 迁移磁盘存档中的旧角色名/显示名引用（profile_dir 已指向编辑的剧本，安全）
                    new_display_name = merged.get("display_name", "")
                    self.state.data._migrate_character_in_chats(
                        name, new_name, dname, new_display_name)
                    self.state.data._delete_character(name)
                    if name in self.state.turn_order:
                        idx = self.state.turn_order.index(name)
                        self.state.turn_order[idx] = new_name
                        self.state.data._save_turn_order()
                self.state.data._reload_data()
                dlg.complete(f"已补全 {dname}", on_close=self._render_detail_body)
            except Exception as ex:
                dlg.fail("保存失败：" + str(ex)[:60])

        def _on_error(msg):
            dlg.fail("补全失败：" + str(msg)[:60])

        try:
            self.state.ai.complete_character_async(name, _on_result, _on_error)
        except Exception as ex:
            dlg.fail("补全失败：" + str(ex)[:60])

    # ── 场景编辑 ──
    def _edit_scene(self, idx):
        sc = self.state.scenes[idx] if idx is not None and idx < len(self.state.scenes) else {}
        time_f = ft.TextField(label="时间", value=sc.get("time", ""), dense=True)
        loc_f = ft.TextField(label="地点", value=sc.get("location", ""), dense=True)
        mood_f = ft.TextField(label="氛围", value=sc.get("mood", ""), dense=True)
        scene_f = ft.TextField(label="场景描述", value=sc.get("scene", ""), multiline=True, min_lines=3, max_lines=6)

        def _save(e=None):
            new_sc = {"time": time_f.value or "", "location": loc_f.value or "",
                      "mood": mood_f.value or "", "scene": scene_f.value or ""}
            if idx is None:
                self.state.scenes.append(new_sc)
            else:
                self.state.scenes[idx] = new_sc
            try:
                self.state.data._save_scenes()
            except Exception:
                pass
            self._close_dialog()
            self._render_detail_body()

        dlg = ft.AlertDialog(
            title=ft.Text("编辑场景" if idx is not None else "添加场景"),
            content=ft.Column(controls=[time_f, loc_f, mood_f, scene_f], tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                ft.FilledButton("保存", on_click=_save),
            ],
        )
        self.page.show_dialog(dlg)

    def _delete_scene(self, idx):
        def _ok(e=None):
            if 0 <= idx < len(self.state.scenes):
                self.state.scenes.pop(idx)
                # 调整 scene_idx 避免越界
                if self.state.scene_idx >= len(self.state.scenes):
                    self.state.scene_idx = max(0, len(self.state.scenes) - 1)
                try:
                    self.state.data._save_scenes()
                except Exception:
                    pass
            self._close_dialog()
            self._render_detail_body()
        dlg = ft.AlertDialog(
            title=ft.Text("删除场景"),
            content=ft.Text("确定删除该场景？"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                ft.FilledButton("删除", on_click=_ok),
            ],
        )
        self.page.show_dialog(dlg)

    # ── 角色编辑 ──
    def _edit_character(self, name):
        c = self.state.characters.get(name, {}) if name else {}
        is_you = name == "You"
        name_f = ft.TextField(label="英文名（唯一）" + ("（不可更改）" if is_you else ""),
                              value=c.get("name", ""), dense=True, read_only=is_you)
        dname_f = ft.TextField(label="显示名", value=c.get("display_name", ""), dense=True)
        color_f = ft.TextField(label="角色色 (#RRGGBB)", value=c.get("color", "#888888"), dense=True)
        pers_f = ft.TextField(label="性格", value=c.get("personality", ""), dense=True)
        desc_f = ft.TextField(label="描述", value=c.get("description", ""), multiline=True, min_lines=2, max_lines=4)
        prompt_f = ft.TextField(label="系统提示词", value=c.get("system_prompt", ""), multiline=True,
                                min_lines=3, max_lines=8)

        def _save(e=None):
            data = {
                "name": "You" if is_you else (name_f.value or dname_f.value or "新角色"),
                "display_name": dname_f.value or name_f.value or "新角色",
                "color": color_f.value or "#888888",
                "bg_color": c.get("bg_color", "#f5f5f5"),
                "personality": pers_f.value or "",
                "description": desc_f.value or "",
                "system_prompt": prompt_f.value or "",
            }
            fname = data["name"] + ".json"
            old_name = name
            try:
                if old_name and old_name != data["name"]:
                    if data["name"] in self.state.characters:
                        self._snack(f"角色名「{data['name']}」已存在，请使用其他名字")
                        return
                    # 迁移 history 中的旧角色名引用
                    # 仅当当前编辑的剧本是活跃剧本时才迁移内存 history
                    active_folder = config.app_config.get("active_profile", "")
                    editing_folder = self.state.profile_dir.name if self.state.profile_dir else ""
                    if editing_folder == active_folder:
                        with self.state._history_lock:
                            for entry in self.state.history:
                                if entry.get("name") == old_name:
                                    entry["name"] = data["name"]
                    # 迁移磁盘存档中的旧角色名/显示名引用
                    old_display_name = c.get("display_name", "")
                    new_display_name = data.get("display_name", "")
                    self.state.data._migrate_character_in_chats(
                        old_name, data["name"], old_display_name, new_display_name)
                    self.state.data._save_character(fname, data)
                    self.state.data._reload_data()
                    if old_name in self.state.turn_order:
                        idx2 = self.state.turn_order.index(old_name)
                        self.state.turn_order[idx2] = data["name"]
                        self.state.data._save_turn_order()
                    self.state.data._delete_character(old_name)
                    self.state.data._reload_data()
                else:
                    self.state.data._save_character(fname, data)
                    self.state.data._reload_data()
            except Exception as ex:
                print(f"[profiles] 保存角色失败: {ex}")
            self._close_dialog()
            self._render_detail_body()

        dlg = ft.AlertDialog(
            title=ft.Text("编辑角色" if name else "新角色"),
            content=ft.Column(controls=[name_f, dname_f, color_f, pers_f, desc_f, prompt_f],
                              tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                ft.FilledButton("保存", on_click=_save),
            ],
        )
        self.page.show_dialog(dlg)

    def _on_char_menu(self, action: str, name: str):
        if action == "delete":
            if name == "You":
                self._snack("用户角色「你」不可删除")
                return
            def _ok(e=None):
                try:
                    self.state.data._delete_character(name)
                    if name in self.state.turn_order:
                        self.state.turn_order.remove(name)
                        self.state.data._save_turn_order()
                    self.state.data._reload_data()
                except Exception:
                    pass
                self._close_dialog()
                self._render_detail_body()
            dlg = ft.AlertDialog(
                title=ft.Text("删除角色"),
                content=ft.Text(f"确定删除角色「{name}」？"),
                actions=[
                    ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                    ft.FilledButton("删除", on_click=_ok),
                ],
            )
            self.page.show_dialog(dlg)
        elif action == "duplicate":
            if name == "You":
                self._snack("用户角色不可复制")
                return
            c = dict(self.state.characters.get(name, {}))
            base = c.get("name", "char") + "_copy"
            new_name = base
            idx = 2
            while new_name in self.state.characters:
                new_name = f"{base}{idx}"
                idx += 1
            c["name"] = new_name
            c["display_name"] = c.get("display_name", "") + " 副本"
            try:
                self.state.data._save_character(c["name"] + ".json", c)
                self.state.data._reload_data()
            except Exception:
                pass
            self._render_detail_body()

    # ── 进入对话 ──
    def _enter_chat(self, folder: str):
        active = config.app_config.get("active_profile", "")
        if folder == active:
            # 同一剧本，直接回聊天（on_enter 会恢复数据）
            self._detail_folder = None
            self.router.navigate("/chat")
            return
        # 不同剧本：提示是否保存当前对话
        has_chat = bool(self.state.history)
        if not has_chat:
            self._do_switch_and_enter(folder)
            return

        def save_and_switch(e=None):
            self._close_dialog()
            self._save_switch_folder = folder
            self._save_switch_done = False
            self._save_timeout_done = False
            self._save_generation += 1  # 新保存代际
            my_gen = self._save_generation  # 捕获本次保存的代际令牌
            # 显示保存进度对话框
            self._save_dialog = ProgressDialog(self.page, title="💾 保存对话")
            self._save_dialog.show(
                status="正在写入对话数据…",
                steps=["写入对话数据", "生成对话标题", "切换剧本"],
                indeterminate=True,
            )
            self._save_dialog.set_step(0, "正在写入对话数据…")

            # 订阅保存事件（改为实例方法，on_leave 可统一清理）
            self.state.bus.on("saving", self._on_save_saving)
            self.state.bus.on("saved", self._on_save_saved)
            # 超时兜底：30s 后标记超时但不取消订阅（再给 30s 宽限期）
            import threading
            def _save_timeout():
                import time as _t
                _t.sleep(30)
                # 代际校验：若期间用户开了新保存，本线程放弃操作
                if my_gen != self._save_generation:
                    return
                if self._save_switch_done:
                    return
                self._save_timeout_done = True
                # 先捕获到局部变量，避免 TOCTOU 竞态
                dlg = self._save_dialog
                if dlg and not self._save_switch_done:
                    # fail 带 on_close：用户 dismiss 超时对话框后置 _save_switch_done=True，
                    # 让下方 60s 分支看到"已结束"而提前 return，避免强制切换
                    def _on_timeout_close():
                        self._save_dialog = None
                        self._save_switch_done = True
                        self._unsubscribe_save_events()
                    dlg.fail("保存超时，请重试", on_close=_on_timeout_close)
                _t.sleep(30)
                # 代际再次校验（30s 宽限期内用户可能开了新保存）
                if my_gen != self._save_generation:
                    return
                # 60s 后仍未完成且用户未 dismiss 超时对话框，强制清理 + 切换
                if not self._save_switch_done:
                    self._save_switch_done = True
                    self._unsubscribe_save_events()
                    if self._save_dialog:
                        try:
                            self._save_dialog.close()
                        except Exception:
                            pass
                        self._save_dialog = None
                    self._do_switch_and_enter(folder)
            threading.Thread(target=_save_timeout, daemon=True).start()
            try:
                self.state.chat.save_current_chat()
            except Exception as ex:
                if my_gen != self._save_generation:
                    return  # 已被新保存取代
                self._unsubscribe_save_events()
                if self._save_dialog:
                    self._save_dialog.fail("保存失败：" + str(ex)[:60],
                        on_close=lambda: self._do_switch_and_enter(folder) if self._save_switch_folder is not None else None)
                    self._save_dialog = None

        def switch_direct(e=None):
            self._close_dialog()
            self._do_switch_and_enter(folder)

        dlg = ft.AlertDialog(
            title=ft.Text("切换剧本"),
            content=ft.Text("当前对话将丢失，是否保存后再切换？"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                ft.OutlinedButton("不保存", on_click=switch_direct),
                ft.FilledButton("保存并切换", on_click=save_and_switch),
            ],
        )
        self.page.show_dialog(dlg)

    def _on_save_saving(self, _data):
        if self._save_dialog:
            self._save_dialog.set_step(1, "正在生成对话标题…", delay=0.1)

    def _on_save_saved(self, data):
        if self._save_switch_done:
            return
        ok = data.get("success", False) if isinstance(data, dict) else False
        title = data.get("title", "") if isinstance(data, dict) else ""
        self._save_switch_done = True
        self._unsubscribe_save_events()
        folder = self._save_switch_folder
        if self._save_dialog:
            if ok:
                summary = f"保存成功（延迟）：{title}" if self._save_timeout_done and title else (
                    "保存成功（延迟）" if self._save_timeout_done else
                    (f"保存成功：{title}" if title else "保存成功")
                )
                self._save_dialog.set_step(2, "正在切换剧本…", delay=0.1)
                # on_close 加守卫：若 on_leave 已置 _save_switch_folder=None（视图已离开），不执行切换
                self._save_dialog.complete(
                    summary,
                    on_close=lambda: self._do_switch_and_enter(folder) if self._save_switch_folder is not None else None,
                    auto_close_ms=800,
                )
            else:
                msg = data.get("message", "保存失败") if isinstance(data, dict) else "保存失败"
                self._save_dialog.fail(msg, on_close=lambda: self._do_switch_and_enter(folder) if self._save_switch_folder is not None else None)
            self._save_dialog = None
        # 若 _save_dialog 已 None（外部关闭），且 folder 仍有效，直接切换
        elif folder is not None and self._save_switch_folder is not None:
            self._do_switch_and_enter(folder)

    def _unsubscribe_save_events(self):
        try:
            self.state.bus.off("saving", self._on_save_saving)
            self.state.bus.off("saved", self._on_save_saved)
        except Exception:
            pass

    def _do_switch_and_enter(self, folder: str):
        try:
            self.state.switch_profile(folder)
        except Exception as ex:
            print(f"[profiles] 切换剧本失败: {ex}")
        self._detail_folder = None
        self.router.navigate("/chat")

    def _open_detail(self, folder: str):
        # 加载该剧本数据到 state 用于查看/编辑，不改变活跃剧本、不停止对话
        try:
            self.state.load_profile_for_edit(folder)
        except Exception as ex:
            print(f"[profiles] 加载剧本失败: {ex}")
        self._detail_folder = folder
        self._render()

    def _back_to_list(self):
        self._detail_folder = None
        self._render()

    # ═══ 卡片菜单 ═══
    def _on_card_menu(self, action: str, folder: str):
        if action == "rename":
            self._rename_dialog(folder)
        elif action == "duplicate":
            self._duplicate_profile(folder)
        elif action == "delete":
            self._delete_dialog(folder)
        elif action == "export":
            self._export_profile(folder)
        elif action == "longpress":
            self._show_card_menu_sheet(folder)

    def _show_card_menu_sheet(self, folder: str):
        # 先清理前一个可能残留的 sheet（遮罩 dismiss 路径可能未清理）
        if self._opened_sheet is not None:
            self._close_sheet()
        meta = gather_profile_meta(folder)
        sheet = ft.BottomSheet(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(meta["title"], size=TEXT_ML, weight=ft.FontWeight.W_600),
                        ft.Divider(height=1),
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.EDIT),
                            title=ft.Text("重命名"),
                            on_click=lambda e: (self._close_sheet(), self._rename_dialog(folder)),
                        ),
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.CONTENT_COPY),
                            title=ft.Text("复制"),
                            on_click=lambda e: (self._close_sheet(), self._duplicate_profile(folder)),
                        ),
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.DELETE_OUTLINE),
                            title=ft.Text("删除"),
                            on_click=lambda e: (self._close_sheet(), self._delete_dialog(folder)),
                        ),
                    ],
                    spacing=4, tight=True,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            ),
            # on_dismiss：用户点击遮罩区域关闭时也走清理路径，避免 overlay 孤儿泄漏
            on_dismiss=lambda e: self._close_sheet(),
        )
        self._opened_sheet = sheet
        # Flet 0.86 的 BottomSheet 需通过 overlay + open=True 显示
        try:
            self.page.overlay.append(sheet)
            sheet.open = True
            self.page.update()
        except Exception as ex:
            print(f"[profiles] 显示底部菜单失败: {ex}")

    def _close_sheet(self):
        try:
            sheet = getattr(self, "_opened_sheet", None)
            if sheet is not None:
                sheet.open = False
                try:
                    self.page.overlay.remove(sheet)
                except (ValueError, KeyError):
                    pass
                self._opened_sheet = None
                self.page.update()
        except Exception:
            pass

    # ── 新建 ──
    def _new_profile_dialog(self):
        field = ft.TextField(label="剧本名称", autofocus=True, on_submit=lambda e: _ok())
        def _ok(e=None):
            name = (field.value or "").strip()
            if not name:
                return
            folder = self.state.data.create_profile(name)
            self._close_dialog()
            if folder:
                self._render()
            else:
                self._snack("创建失败：名称可能重复")
        dlg = ft.AlertDialog(
            title=ft.Text("新建剧本"),
            content=ft.Column(controls=[field, ft.Text("可稍后在剧本详情中添加角色与场景",
                                                       size=TEXT_XS, color=ft.Colors.ON_SURFACE_VARIANT)],
                             tight=True),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                ft.FilledButton("创建", on_click=_ok),
            ],
        )
        self.page.show_dialog(dlg)

    # ── 重命名 ──
    def _rename_dialog(self, folder: str):
        meta = gather_profile_meta(folder)
        field = ft.TextField(label="新名称", value=meta["title"], autofocus=True)
        def _ok(e=None):
            name = (field.value or "").strip()
            if not name:
                return
            ok = self.state.data.rename_profile(folder, name)
            self._close_dialog()
            self._snack("已重命名" if ok else "重命名失败")
            self._render()
        dlg = ft.AlertDialog(
            title=ft.Text("重命名剧本"),
            content=field,
            actions=[
                ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                ft.FilledButton("保存", on_click=_ok),
            ],
        )
        self.page.show_dialog(dlg)

    # ── 删除 ──
    def _delete_dialog(self, folder: str):
        meta = gather_profile_meta(folder)
        if len(self.state.data.get_profile_list()) <= 1:
            self._snack("至少保留一个剧本")
            return
        def _ok(e=None):
            ok = self.state.data.delete_profile(folder)
            self._close_dialog()
            self._snack("已删除" if ok else "删除失败")
            if folder == config.app_config.get("active_profile"):
                rest = self.state.data.get_profile_list()
                if rest:
                    self.state.switch_profile(rest[0])
            self._render()
        dlg = ft.AlertDialog(
            title=ft.Text("删除剧本"),
            content=ft.Text(f"确定删除「{meta['title']}」？所有角色/场景/存档将丢失。"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                ft.FilledButton("删除", on_click=_ok, style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR)),
            ],
        )
        self.page.show_dialog(dlg)

    # ── 复制 ──
    def _duplicate_profile(self, folder: str):
        meta = gather_profile_meta(folder)
        new_name = meta["title"] + " 副本"
        new_folder = self.state.data.create_profile(new_name)
        if not new_folder:
            self._snack("复制失败：名称冲突")
            return
        src = config.PROFILES_DIR / folder
        dst = config.PROFILES_DIR / new_folder
        try:
            for sub in ("characters", "chats"):
                sdir = src / sub
                if sdir.exists():
                    (dst / sub).mkdir(exist_ok=True)
                    for f in sdir.glob("*.json"):
                        # 不复制自动存档（避免副本启动时弹出恢复提示）
                        if f.name == "_autosave.json":
                            continue
                        shutil.copy2(str(f), str(dst / sub / f.name))
            shutil.copy2(str(src / "scenes.json"), str(dst / "scenes.json"))
            # 复制 config 但改 title
            from utils import load_json, save_json
            pc = load_json(src / "config.json", default={})
            pc.setdefault("app", {})["title"] = new_name
            save_json(dst / "config.json", pc)
        except Exception as ex:
            print(f"[profiles] 复制失败: {ex}")
            self._snack("复制失败")
            return
        self._snack("已复制")
        self._render()

    # ── 导出 ──
    def _export_profile(self, folder: str):
        if getattr(self.page, "web", False):
            self._snack("Web 端暂不支持导出，请在桌面端操作")
            return
        import zipfile, tempfile, os
        src = config.PROFILES_DIR / folder
        meta = gather_profile_meta(folder)
        safe = folder
        out_dir = config.BASE_DIR / "exports"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / f"{safe}.zip"
        try:
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in src.rglob("*"):
                    if p.is_file():
                        zf.write(p, arcname=p.relative_to(src))
            self._snack(f"已导出：{out_path}")
        except Exception as ex:
            print(f"[profiles] 导出失败: {ex}")
            self._snack("导出失败")

    # ── AI 创建（三步）──
    def _ai_create_dialog(self):
        if not config.API_KEY:
            self._snack("请先在设置中配置 API Key")
            return
        self._ai_step1()

    def _ai_step1(self):
        desc_f = ft.TextField(
            label="描述你想要的剧本",
            hint_text="如：四个魔法学院的女学生室友的日常",
            multiline=True, min_lines=3, max_lines=6, autofocus=True,
        )

        def _start(e=None):
            desc = (desc_f.value or "").strip()
            if not desc:
                return
            self._close_dialog()
            self._ai_step2(desc)

        dlg = ft.AlertDialog(
            title=ft.Text("✨ AI 创建剧本"),
            content=ft.Column(
                controls=[
                    desc_f,
                    ft.Text("示例：星际飞船上五名船员的冒险 / 魔法学院室友的日常",
                            size=TEXT_XS, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                ft.FilledButton("开始生成", icon=ft.Icons.AUTO_AWESOME, on_click=_start),
            ],
        )
        self.page.show_dialog(dlg)

    def _ai_step2(self, desc: str):
        if self.state.history:
            def _proceed(e=None):
                self._close_dialog()
                self._ai_step2_generate(desc)
            dlg = ft.AlertDialog(
                title=ft.Text("提示"),
                content=ft.Text("当前有进行中的对话，AI 创建新剧本会清空当前对话并切换到新剧本。确定继续？"),
                actions=[
                    ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                    ft.FilledButton("确定", on_click=_proceed),
                ],
            )
            self.page.show_dialog(dlg)
            return
        self._ai_step2_generate(desc)

    def _ai_step2_generate(self, desc: str):
        pdlg = ProgressDialog(self.page, title="✨ 生成中")
        _steps = ["分析描述", "生成世界观", "生成场景", "生成角色", "写入剧本"]
        pdlg.show(
            status="正在分析描述…",
            steps=_steps,
            indeterminate=True,
        )
        pdlg.set_step(0, "正在分析描述…")

        _current_step = [0]  # track which step icon is active

        def _advance_step(new_idx, status):
            if new_idx > _current_step[0]:
                _current_step[0] = new_idx
                pdlg.set_step(new_idx, status, delay=0.08)

        def _on_plan_ready(blueprint):
            _current_step[0] = 0
            _advance_step(1, "正在生成世界观…")

        _phase_labels = {"scene": "生成场景", "char": "生成角色", "writing": "写入剧本"}
        _step_defaults = {1: "正在生成世界观…", 2: "正在生成场景…", 3: "正在生成角色…", 4: "正在写入剧本…"}

        def _on_phase_progress(phase, task_name, phase_done, phase_total, step_idx):
            default_status = _step_defaults.get(step_idx)
            _advance_step(step_idx, default_status)
            label = _phase_labels.get(phase, "生成中")
            if phase_total > 0:
                pdlg.set_progress_fraction(phase_done, phase_total, label)
            else:
                pdlg.set_status(f"{label} (0/0)")

        def _on_all_done(results, errors):
            try:
                _advance_step(4, "正在保存剧本…")
                world = results.get("world", "")
                title = results.get("title", "新剧本")
                folder = self.state.data.create_profile(title)
                if not folder:
                    pdlg.fail("创建失败：名称冲突")
                    return
                self.state.switch_profile(folder)
                self.state._profile_config.setdefault("world", {})["setting"] = world

                # 场景
                scene_list = []
                for s in results.get("scenes", []):
                    if s and isinstance(s, dict) and s.get("time"):
                        scene_list.append(s)
                self.state.scenes = scene_list if scene_list else self.state.scenes
                self.state.data._save_scenes()

                # 角色
                written_names = set()
                for cname in sorted(results.get("characters", {}).keys()):
                    c = results["characters"][cname]
                    safe_name = c.get("name", cname)
                    if safe_name in written_names or safe_name == "You":
                        base = safe_name
                        idx = 2
                        while base in written_names or base == "You":
                            base = f"{safe_name}{idx}"
                            idx += 1
                        safe_name = base
                    written_names.add(safe_name)
                    c["name"] = safe_name
                    c.setdefault("color", "#888888")
                    c.setdefault("bg_color", "#f5f5f5")
                    self.state.data._save_character(safe_name + ".json", c)

                # You 角色
                you = results.get("you")
                if you:
                    you.setdefault("color", "#42a5f5")
                    you.setdefault("bg_color", "#f0f7ff")
                    self.state.data._save_character("You.json", you)
                elif "You" not in self.state.characters:
                    self.state.data._save_character("You.json", {
                        "name": "You", "display_name": "你",
                        "color": "#42a5f5", "bg_color": "#f0f7ff",
                        "personality": "你自己",
                        "description": "就是你自己～一个和大家一起生活的普通人。",
                        "system_prompt": "你是这个世界的一员，和伙伴们自然地聊天。对话内容用直角引号「」包裹，动作描写用*星号*包裹，例如：*伸了个懒腰*、*笑着拍拍她的肩*。回复简短自然，100-200字。",
                    })

                # 发言顺序
                order = [c.get("name") for c in (results.get("characters", {}) or {}).values() if c.get("name")]
                order.append("You")
                self.state.turn_order = [n for n in order if n]
                self.state.data._save_turn_order()
                self.state.data._save_profile_config()
                self.state.data._reload_data()

                n_chars = len(written_names) + 1
                n_scenes = len(scene_list)
                if errors:
                    failed = "、".join(errors)
                    pdlg.complete(
                        f"已生成「{title}」· {n_chars} 角色 · {n_scenes} 场景（部分失败: {failed}）",
                        on_close=lambda: self._ai_step3(folder, title, n_chars, n_scenes),
                    )
                else:
                    pdlg.complete(
                        f"已生成「{title}」· {n_chars} 角色 · {n_scenes} 场景",
                        on_close=lambda: self._ai_step3(folder, title, n_chars, n_scenes),
                    )
            except Exception as ex:
                print(f"[ai_create] 填充剧本失败: {ex}")
                pdlg.fail("写入失败：" + str(ex)[:80])

        def _on_error(msg):
            pdlg.fail("生成失败：" + str(msg)[:80])

        try:
            self.state.ai.generate_profile_batch_async(
                desc,
                on_plan_ready=_on_plan_ready,
                on_phase_progress=_on_phase_progress,
                on_all_done=_on_all_done,
                on_error=_on_error,
            )
        except Exception as ex:
            pdlg.fail("生成失败：" + str(ex)[:80])

    def _ai_step3(self, folder: str, title: str, n_chars: int, n_scenes: int):
        def _enter(e=None):
            self._close_dialog()
            self._detail_folder = None
            self.router.navigate("/chat")

        def _edit(e=None):
            self._close_dialog()
            self._open_detail(folder)

        dlg = ft.AlertDialog(
            title=ft.Text("✨ 生成完成"),
            content=ft.Column(
                controls=[
                    ft.Text(f"已生成「{title}」", size=TEXT_MD, weight=ft.FontWeight.W_600),
                    ft.Text(f"{n_chars} 角色 · {n_scenes} 场景", size=TEXT_SM,
                            color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("再改改", on_click=_edit),
                ft.FilledButton("进入剧本", icon=ft.Icons.PLAY_ARROW, on_click=_enter),
            ],
        )
        self.page.show_dialog(dlg)

    # ═══ 工具 ═══
    def _close_dialog(self):
        try:
            self.page.pop_dialog()
        except Exception:
            pass

    def on_enter(self):
        if not self._built:
            return
        self._render()

    def on_leave(self):
        # 清理保存订阅，避免跨视图 saved 事件串扰
        self._unsubscribe_save_events()
        # 关闭挂起的保存对话框，避免跨视图悬挂
        if self._save_dialog:
            try:
                self._save_dialog.close()
            except Exception:
                pass
            self._save_dialog = None
        # 关闭挂起的底部菜单 sheet
        if self._opened_sheet is not None:
            self._close_sheet()
        # 关键：置 _save_switch_done=True 向旧超时线程发"已结束"信号，避免其复活强制切换；
        # 置 _save_switch_folder=None 作为 on_close lambda 的守卫（lambda 检查 None 则不切换）；
        # bump 代际令牌让旧超时线程识别"我已过期"而提前 return。
        # 下次 save_and_switch 开头会把它们重置为 False / folder + bump 新代际，不影响新流程。
        self._save_switch_folder = None
        self._save_switch_done = True
        self._save_timeout_done = False
        self._save_generation += 1
