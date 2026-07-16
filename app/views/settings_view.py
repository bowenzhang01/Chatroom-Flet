# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · 设置视图
  分区卡片：API 配置 / 外观 / 默认行为 / 关于
  API：地址 / Key(密码+显隐) / 模型+刷新 / 温度 / 最大tokens / 测试连接+保存
  外观：主题模式 / 字号
  默认行为：导演/用户/动态场景/随机事件 Switch ×4 / 默认模式 / 默认速度
  关于：版本 / GitHub / 反馈 / 许可证
"""

import flet as ft

import config
from app.views import ViewBase
from app.theme import THEME_MODES, COLORS
from services.api_service import test_connection_async, fetch_models_async

__all__ = ["SettingsView"]

_THEME_LABELS = {"light": "浅色", "dark": "深色", "system": "跟随系统"}
_VERSION = "0.1.0-flet"


class SettingsView(ViewBase):
    def __init__(self, page, app_state, ui_state, router):
        super().__init__(page, app_state, ui_state, router)
        self._built = False
        self._api_status_dot: ft.Container = None
        self._key_field: ft.TextField = None
        self._model_dd: ft.Dropdown = None
        self._temp_slider: ft.Slider = None
        self._tokens_slider: ft.Slider = None
        self._test_result: ft.Text = None
        self._test_progress: ft.ProgressRing = None
        self._director_sw: ft.Switch = None
        self._user_sw: ft.Switch = None
        self._dynamic_sw: ft.Switch = None
        self._random_sw: ft.Switch = None
        self._mode_dd: ft.Dropdown = None
        self._speed_dd: ft.Dropdown = None

    def build(self) -> ft.Control:
        self._root = ft.Column(
            controls=[
                self._build_title(),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self._build_api_card(),
                            self._build_appearance_card(),
                            self._build_behavior_card(),
                            self._build_about_card(),
                        ],
                        spacing=12,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                    padding=ft.Padding.all(16),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
        self._built = True
        return self._root

    def _build_title(self) -> ft.Control:
        return ft.Container(
            content=ft.Text("设置", size=20, weight=ft.FontWeight.W_700),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    # ═══ 卡片容器 ═══
    def _card(self, title: str, controls: list) -> ft.Control:
        head = [ft.Text(title, size=15, weight=ft.FontWeight.W_600)] if title else []
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=head + controls,
                    spacing=10,
                    tight=True,
                ),
                padding=ft.Padding.all(16),
            ),
            elevation=0,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        )

    # ═══ API 配置 ═══
    def _build_api_card(self) -> ft.Control:
        mc = config.app_config.get("model", {})
        self._api_status_dot = ft.Container(width=10, height=10, border_radius=5,
                                            bgcolor=ft.Colors.OUTLINE)
        connected = bool(config.API_KEY)

        base_f = ft.TextField(label="API 地址", value=config.API_BASE, dense=True)
        self._key_field = ft.TextField(
            label="API Key", value=config.API_KEY, dense=True,
            password=True, can_reveal_password=True,
        )
        self._model_dd = ft.Dropdown(
            value=config.MODEL,
            options=[ft.dropdown.Option(m) for m in (config.MODELS_LIST or [config.MODEL])],
            dense=True, expand=True,
        )
        refresh_btn = ft.IconButton(
            icon=ft.Icons.REFRESH, tooltip="刷新模型列表",
            on_click=lambda e: self._fetch_models(base_f.value, self._key_field.value),
        )
        self._temp_slider = ft.Slider(
            min=0, max=2, divisions=20, value=float(config.TEMPERATURE),
            label="{value}", expand=True,
        )
        self._tokens_slider = ft.Slider(
            min=100, max=4000, divisions=39, value=float(config.MAX_TOKENS),
            label="{value}",
        )
        self._test_result = ft.Text("", size=12)
        self._test_progress = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=2)

        def _test(e=None):
            self._test_result.value = ""
            self._test_progress.visible = True
            self.page.update()
            import time
            t0 = time.time()

            def _on_result(ok, msg):
                elapsed = int((time.time() - t0) * 1000)
                self._test_progress.visible = False
                if ok:
                    self._test_result.value = f"✓ 连接正常，延迟 {elapsed}ms"
                    self._test_result.color = ft.Colors.TERTIARY
                    self._api_status_dot.bgcolor = ft.Colors.TERTIARY
                else:
                    self._test_result.value = f"✗ {msg}"
                    self._test_result.color = ft.Colors.ERROR
                    self._api_status_dot.bgcolor = ft.Colors.ERROR
                self.page.update()

            test_connection_async(_on_result, api_key=self._key_field.value,
                                  api_base=base_f.value)

        def _save(e=None):
            mc2 = config.app_config.setdefault("model", {})
            mc2["api_base"] = base_f.value or config.API_BASE
            mc2["api_key"] = self._key_field.value or ""
            mc2["model"] = self._model_dd.value or config.MODEL
            mc2["temperature"] = float(self._temp_slider.value)
            mc2["max_tokens"] = int(self._tokens_slider.value)
            mc2["models"] = [o.key for o in self._model_dd.options] if self._model_dd.options else config.MODELS_LIST
            try:
                self.state.data._save_config()
            except Exception:
                pass
            # 更新模块级变量
            config.API_KEY = self._key_field.value or ""
            config.API_BASE = base_f.value or config.API_BASE
            config.MODEL = self._model_dd.value or config.MODEL
            config.TEMPERATURE = float(self._temp_slider.value)
            config.MAX_TOKENS = int(self._tokens_slider.value)
            self._api_status_dot.bgcolor = ft.Colors.TERTIARY if config.API_KEY else ft.Colors.OUTLINE
            self.page.update()
            self._snack("已保存 API 配置")

        return self._card("", [
            ft.Row([ft.Text("API 配置", size=15, weight=ft.FontWeight.W_600),
                    self._api_status_dot,
                    ft.Text("已连接" if connected else "未配置", size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT)], spacing=8),
            base_f,
            self._key_field,
            ft.Row([self._model_dd, refresh_btn], spacing=8,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text("温度", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            self._temp_slider,
            ft.Text("最大 tokens", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            self._tokens_slider,
            ft.Row([self._test_progress, self._test_result], spacing=8,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                ft.OutlinedButton("测试连接", icon=ft.Icons.NETWORK_CHECK, on_click=_test),
                ft.FilledButton("保存", icon=ft.Icons.SAVE, on_click=_save),
            ], spacing=8),
        ])

    def _fetch_models(self, base, key):
        self._model_dd.options = []
        self.page.update()

        def _on_result(models):
            if models:
                config.MODELS_LIST = models
                self._model_dd.options = [ft.dropdown.Option(m) for m in models]
                if config.MODEL in models:
                    self._model_dd.value = config.MODEL
                self.page.update()
                self._snack(f"获取到 {len(models)} 个模型")
            else:
                self._snack("未获取到模型")

        def _on_error(msg):
            self._snack("获取模型失败：" + str(msg)[:60])

        fetch_models_async(_on_result, on_error=_on_error, api_key=key, api_base=base)

    # ═══ 外观 ═══
    def _build_appearance_card(self) -> ft.Control:
        seg = ft.SegmentedButton(
            selected=[self.ui.theme_mode_key],
            segments=[ft.Segment(value=k, label=ft.Text(v, size=12)) for k, v in _THEME_LABELS.items()],
            allow_multiple_selection=False, allow_empty_selection=False,
            on_change=self._on_theme_change,
        )
        font_slider = ft.Slider(min=12, max=20, divisions=8, value=14, label="{value}",
                                on_change=self._on_font_change)
        return self._card("外观", [
            ft.Text("主题模式", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            seg,
            ft.Container(height=4),
            ft.Text("字体大小（部分控件预览）", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            font_slider,
        ])

    def _on_theme_change(self, e):
        sel = e.control.selected
        if sel:
            if isinstance(sel, (list, tuple)):
                self.ui.theme_mode_key = sel[0]
            elif isinstance(sel, set):
                self.ui.theme_mode_key = next(iter(sel))
            self.ui.save_theme_mode()
            self.page.theme_mode = THEME_MODES[self.ui.theme_mode_key]
            self.page.update()

    def _on_font_change(self, e):
        size = int(e.control.value)
        ui = config.app_config.setdefault("ui", {})
        ui["font_size"] = size
        try:
            from utils import save_json
            save_json(config.BASE_DIR / "config.json", config.app_config)
        except Exception:
            pass

    # ═══ 默认行为 ═══
    def _build_behavior_card(self) -> ft.Control:
        # 从当前剧本配置读取（而非全局 config.app_config）
        pc = self.state._profile_config.setdefault("app", {})
        self._director_sw = ft.Switch(label="导演模式", value=self.state.director_mode)
        self._user_sw = ft.Switch(label="用户模式", value=self.state.user_mode)
        self._dynamic_sw = ft.Switch(label="动态场景", value=self.state.dynamic_scene_enabled)
        self._random_sw = ft.Switch(label="随机事件", value=self.state.random_event_enabled)

        def _persist(e=None):
            pc["director_mode"] = self._director_sw.value
            pc["user_mode"] = self._user_sw.value
            pc["dynamic_scene"] = self._dynamic_sw.value
            pc["random_event"] = self._random_sw.value
            # 立即更新运行时状态
            self.state.director_mode = self._director_sw.value
            self.state.dynamic_scene_enabled = self._dynamic_sw.value
            self.state.random_event_enabled = self._random_sw.value
            # 用户模式：同步 turn_order 中的 You
            if self._user_sw.value != self.state.user_mode:
                self.state.user_mode = self._user_sw.value
                if self._user_sw.value:
                    if "You" in self.state.characters and "You" not in self.state.turn_order:
                        self.state.turn_order.append("You")
                else:
                    if "You" in self.state.turn_order:
                        self.state.turn_order.remove("You")
                try:
                    self.state.data._save_turn_order()
                except Exception:
                    pass
            try:
                self.state.data._save_profile_config()
            except Exception:
                pass
        for sw in (self._director_sw, self._user_sw, self._dynamic_sw, self._random_sw):
            sw.on_change = _persist

        self._mode_dd = ft.Dropdown(
            value=self.state.mode if self.state.mode in ("round", "random", "dynamic") else "round",
            options=[ft.dropdown.Option(v, text=l) for l, v in [("轮流", "round"), ("随机", "random"), ("动态", "dynamic")]],
            dense=True, width=140,
            on_select=lambda e: self._save_default("default_mode", e.control.value),
        )
        self._speed_dd = ft.Dropdown(
            value=str(self.state.speed),
            options=[ft.dropdown.Option(str(i), text=f"速度 {i}") for i in range(1, 11)],
            dense=True, width=140,
            on_select=lambda e: self._save_default("default_speed", int(e.control.value)),
        )
        return self._card("对话行为（当前剧本，立即生效）", [
            self._director_sw, self._user_sw, self._dynamic_sw, self._random_sw,
            ft.Container(height=4),
            ft.Text("发言模式", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            self._mode_dd,
            ft.Text("速度", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            self._speed_dd,
        ])

    def _save_default(self, key, value):
        pc = self.state._profile_config
        if key == "default_mode":
            pc.setdefault("mode", {})["default"] = value
            self.state.mode = value
        elif key == "default_speed":
            pc.setdefault("speed", {})["default"] = value
            self.state.speed = max(1, min(10, value))
        try:
            self.state.data._save_profile_config()
        except Exception:
            pass

    # ═══ 关于 ═══
    def _build_about_card(self) -> ft.Control:
        return self._card("关于", [
            ft.Row([ft.Text("版本", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(_VERSION, size=12)], spacing=12),
            ft.Row([ft.Text("框架", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text("Flet 0.86.0", size=12)], spacing=12),
            ft.Row([ft.Text("主题", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text("蓝白暮光 Soft Twilight", size=12)], spacing=12),
            ft.Container(height=4),
            ft.Text("问题反馈：请在项目仓库提交 Issue", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Text("许可证：MIT", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
        ])

    # ═══ 工具 ═══
    def _close_dialog(self):
        try:
            self.page.pop_dialog()
        except Exception:
            pass

    def on_enter(self):
        if not self._built:
            return
        # 如果在剧本编辑页加载了其他剧本，恢复活跃剧本数据
        # 否则设置页会编辑错误剧本的配置
        active = config.app_config.get("active_profile", "")
        if active and self.state.profile_dir:
            current_folder = self.state.profile_dir.name
            if current_folder != active:
                self.state.data.load_profile(active)
        self._render_behavior()

    def _render_behavior(self):
        """从 state 同步行为卡片的开关/下拉值。"""
        if self._director_sw:
            self._director_sw.value = self.state.director_mode
        if self._user_sw:
            self._user_sw.value = self.state.user_mode
        if self._dynamic_sw:
            self._dynamic_sw.value = self.state.dynamic_scene_enabled
        if self._random_sw:
            self._random_sw.value = self.state.random_event_enabled
        if self._mode_dd:
            self._mode_dd.value = self.state.mode if self.state.mode in ("round", "random", "dynamic") else "round"
        if self._speed_dd:
            self._speed_dd.value = str(self.state.speed)
        try:
            self.page.update()
        except Exception:
            pass
