# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 事件总线
  替代 Kivy 版的 `Queue + Clock.schedule_interval(poll_queue)` 轮询模型。

  工作原理：
  - 后台对话线程通过 bus.emit(event, data) 发送事件
  - UI 层通过 bus.on(event, handler) 订阅
  - handler 在 emit 的调用线程中执行；Flet 的 page.update() 是跨线程安全的，
    因此后台线程可直接 emit，UI handler 内更新控件无需额外调度

  事件清单（与旧版 queue 命令对应）：
    "msg"              → 新角色消息 (entry: {name, display_name, text, time})
    "user_msg"         → 用户消息已发送 (entry)
    "random_event_msg" → 随机事件消息 (entry)
    "random_npc_msg"   → 路人 NPC 消息 (entry, 可能含 is_farewell=True)
    "user_turn"        → 轮到用户发言 (val=None)
    "set_status"       → 状态栏更新 (val=str)
    "scene_changed"    → 场景切换 (val={time, location, scene, mood, version})
    "api_error_stop"   → API 连续失败，停止对话 (val=error_msg)
    "started"          → 对话已启动
    "paused"           → 对话已暂停
    "resumed"          → 对话已恢复
    "stopped"          → 对话已停止/重置
    "saved"            → 对话已保存 (val={title, success})
    "autosave_prompt"  → 启动时检测到自动存档 (val={title, message_count, path})
"""

from collections import defaultdict
from typing import Any, Callable


class EventBus:
    """轻量级事件总线。线程安全（订阅/触发使用 dict 原子操作）。"""

    def __init__(self):
        self._subs: dict[str, list[Callable[[Any], None]]] = defaultdict(list)

    def on(self, event: str, handler: Callable[[Any], None]) -> None:
        """订阅事件。返回的 handler 可用于之后 off()。"""
        self._subs[event].append(handler)

    def off(self, event: str, handler: Callable[[Any], None]) -> None:
        """取消订阅。"""
        if handler in self._subs[event]:
            self._subs[event].remove(handler)

    def emit(self, event: str, data: Any = None) -> None:
        """触发事件。handler 在当前线程同步执行。
        单个 handler 异常不会影响其他 handler。"""
        for h in list(self._subs[event]):
            try:
                h(data)
            except Exception as e:
                print(f"[EventBus] handler 异常 event={event}: {e}")

    def clear(self) -> None:
        """清空所有订阅（切换剧本/重置时调用）。"""
        self._subs.clear()
