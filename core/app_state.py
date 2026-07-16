# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 应用状态中心
  替代 Kivy 版 DormApp 的 self.xxx 散落属性。
  - 持有所有运行时状态（剧本/角色/场景/对话/模式）
  - 聚合 AIEngine / ChatManager / DataManager / DialogueLoop / EventBus
  - 零 UI 框架依赖：UI 层（app/）读取此对象状态，core 层读写此对象状态

  UI 层用法：
    state = AppState()
    state.load_profile("dorm_life")
    state.loop.start()           # 启动对话
    state.bus.on("msg", handler) # 订阅消息事件
"""

from typing import Optional

from core.events import EventBus
from core.ai_engine import AIEngine
from core.chat_manager import ChatManager
from core.data_manager import DataManager
from core.dialogue_loop import DialogueLoop

import config


class AppState:
    """应用全局状态 + 业务层聚合。"""

    def __init__(self):
        # ── 事件总线 ──
        self.bus = EventBus()

        # ── 业务层（注入 self 引用）──
        self.ai = AIEngine(self)
        self.chat = ChatManager(self)
        self.data = DataManager(self)
        self.loop = DialogueLoop(self)

        # ── 当前剧本数据 ──
        self.profile_dir = None
        self.char_dir = None
        self._profile_config = {}
        self.title = "ChatRoom"

        # ── 场景 ──
        self.scenes: list = []
        self.scene_idx: int = 0
        self.current_scene: Optional[dict] = None
        self.scene_version: int = 0
        self._last_scene_update_turn: int = -1
        self.dynamic_scene_enabled: bool = False

        # ── 角色 ──
        self.characters: dict = {}
        self.char_styles: dict = {}

        # ── 发言顺序与模式 ──
        self.turn_order: list = []
        self.turn_idx: int = 0
        self.turn_count: int = 0
        self.mode: str = "round"  # round | random | dynamic
        self.speed: int = 3

        # ── 对话历史 ──
        self.history: list = []
        self.message_count: int = 0

        # ── 模式开关 ──
        self.director_mode: bool = False
        self.user_mode: bool = False
        self.random_event_enabled: bool = False

        # ── 运行时状态 ──
        self.running: bool = False
        self.paused: bool = False

        # ── 动态发言追踪 ──
        self._char_last_turn: dict = {}
        self._suggested_next: Optional[str] = None

        # ── 随机事件 / NPC 状态 ──
        self._last_random_event_turn: int = 0
        self._char_turns_since_event: int = 0
        self._active_npc: Optional[dict] = None
        self._npc_silent_turns: int = 0
        self._npc_rounds_left: int = 0

        # ── API 错误计数 ──
        self._api_error_count: int = 0

    # ═══ 便捷方法 ═══

    def _get_effective_order(self) -> list:
        """当前模式下的有效发言顺序（含用户角色，仅含存在角色）。"""
        if self.user_mode:
            return [n for n in self.turn_order if n in self.characters]
        return [n for n in self.turn_order if n in self.characters and n != "You"]

    def load_profile(self, profile_name: str):
        """加载剧本。"""
        self.data.load_profile(profile_name)
        config.ACTIVE_PROFILE = profile_name
        config.app_config["active_profile"] = profile_name
        self.data._save_config()

    def load_profile_for_edit(self, profile_name: str):
        """加载剧本数据到 state 用于查看/编辑，不改变活跃剧本、不停止对话。

        用于剧本详情页：用户可能只是在浏览/编辑，不应清空当前对话。
        返回聊天页时 on_enter 会自动恢复活跃剧本的数据。
        """
        self.data.load_profile(profile_name)

    def switch_profile(self, new_name: str):
        """切换剧本（停止对话 + 清空上下文 + 加载新剧本）。

        loop.reset() 会清空 history 和运行时状态；
        不调用 bus.clear() — chat_view 通过 on_leave/on_enter 管理订阅生命周期。
        """
        if new_name == config.app_config.get("active_profile", ""):
            return
        self.loop.reset()
        self.load_profile(new_name)
        self.scene_idx = 0
        self.current_scene = None
        self.scene_version = 0
        self._last_scene_update_turn = -1

    def init_workspace(self):
        """应用启动时调用：路径初始化 + 迁移 + 加载默认剧本。"""
        from services.path_resolver import setup_workspace
        setup_workspace()
        self.data._migrate_if_needed()
        self.load_profile(config.ACTIVE_PROFILE)

    def check_autosave_on_start(self):
        """启动后检查自动存档（延迟调用）。"""
        self.chat.check_autosave_on_start()

    def auto_save(self):
        """手动触发自动存档（生命周期事件时调用）。"""
        self.chat._auto_save()
