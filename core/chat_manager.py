# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 对话存档管理器
  迁移自 Kivy 版 core/chat_manager.py，零 UI 框架依赖。
  - 业务逻辑（存档读写 / AI 标题生成 / 自动存档 / 启动恢复检测）保留
  - 所有 UI 弹窗代码删除（保存中/保存成功/恢复询问）
    改由 EventBus 通知 UI 层：
      "saving"          → 正在保存（UI 显示进度）
      "saved"           → 保存完成 (val={title, success, path})
      "autosave_prompt" → 启动时检测到自动存档 (val={title, message_count, path})
"""

import re
import time
from datetime import datetime
from pathlib import Path

import config
from utils import load_json, save_json, extract_json
from services.api_service import call_chat_completion_async


class ChatManager:
    """对话存档管理 — 通过 app 引用读取状态，通过 bus 通知 UI。"""

    def __init__(self, app):
        self.app = app
        self.bus = app.bus  # 事件总线引用
        self._loaded_chat_path = None   # 记录加载的对话路径，保存时覆盖
        self._last_save_time = 0.0      # 上次保存时间戳
        self._last_autosave_len = 0     # 上次自动存档时的消息数

    @property
    def chats_dir(self) -> Path:
        """当前剧本的对话存档目录"""
        return self.app.profile_dir / "chats" if self.app.profile_dir else None

    def _ensure_chats_dir(self):
        if self.chats_dir and not self.chats_dir.exists():
            self.chats_dir.mkdir(parents=True, exist_ok=True)

    # ── 列表与元信息 ──

    def _list_chat_files(self):
        """列出对话文件，按文件名时间戳倒序（新的在前）"""
        if not self.chats_dir or not self.chats_dir.exists():
            return []
        files = list(self.chats_dir.glob("chat_*.json"))
        def _sort_key(fp):
            m = re.search(r'chat_(\d{8}_\d{6})', fp.name)
            return m.group(1) if m else "00000000_000000"
        files.sort(key=_sort_key, reverse=True)
        return files

    def list_autosave(self):
        """获取自动存档路径（若存在且非空）"""
        if not self.chats_dir:
            return None
        p = self.chats_dir / "_autosave.json"
        if p.exists():
            data = load_json(p)
            if data and data.get("history"):
                return p
        return None

    def _read_chat_meta(self, filepath):
        """读取对话文件的元信息（title, message_count, created_at）"""
        try:
            data = load_json(filepath)
            if not data:
                return None
            return {
                "title": data.get("title", filepath.stem),
                "message_count": data.get("message_count", 0),
                "created_at": data.get("created_at", ""),
                "is_autosave": filepath.name == "_autosave.json",
            }
        except Exception:
            return None

    def list_chats_with_meta(self):
        """列出所有对话存档（含元信息）。返回 [(path, meta), ...]"""
        result = []
        # 自动存档置顶
        autosave = self.list_autosave()
        if autosave:
            meta = self._read_chat_meta(autosave)
            if meta:
                result.append((autosave, meta))
        # 普通存档
        for fp in self._list_chat_files():
            meta = self._read_chat_meta(fp)
            if meta:
                result.append((fp, meta))
        return result

    # ── 保存 ──

    def _save_chat_to_file(self, filepath, title):
        """将当前对话写入文件（底层）。"""
        data = {
            "title": title,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message_count": len(self.app.history),
            "scene_idx": self.app.scene_idx,
            "turn_idx": self.app.turn_idx,
            "turn_count": self.app.turn_count,
            "history": list(self.app.history),
        }
        return save_json(filepath, data)

    def _fallback_chat_title(self) -> str:
        """AI 不可用时的备选标题：剧本名 - 场景时间 - HH:MM"""
        ac = self.app._profile_config.get("app", {})
        profile_name = ac.get("title", self.app.title)
        scene_time = (self.app.scenes[self.app.scene_idx].get("time", "")
                      if self.app.scenes and self.app.scene_idx < len(self.app.scenes) else "")
        now = datetime.now().strftime("%H:%M")
        parts = [profile_name]
        if scene_time:
            parts.append(scene_time)
        parts.append(now)
        return " - ".join(parts)

    def save_current_chat(self, show_feedback=True):
        """保存当前对话（含 AI 标题生成）。
        通过 bus 发 "saving" 和 "saved" 事件。"""
        if not self.app.history:
            if show_feedback:
                self.bus.emit("saved", {"title": "", "success": False,
                                        "message": "没有对话内容可保存", "path": None})
            return

        self._ensure_chats_dir()
        if self._loaded_chat_path is not None:
            filepath = self._loaded_chat_path
            self._loaded_chat_path = None
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.chats_dir / f"chat_{ts}.json"

        # 快照（防竞态：保存→AI标题→回写 期间 history 可能被清空）
        saved_data = {
            "title": "保存中...",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message_count": len(self.app.history),
            "scene_idx": self.app.scene_idx,
            "turn_idx": self.app.turn_idx,
            "turn_count": self.app.turn_count,
            "history": list(self.app.history),
        }
        save_json(filepath, saved_data)

        if show_feedback:
            self.bus.emit("saving", None)

        _caller_profile = config.app_config.get("active_profile", "")

        def _on_title_ready(title):
            if config.app_config.get("active_profile", "") != _caller_profile:
                return
            saved_data["title"] = title
            saved_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_json(filepath, saved_data)
            self._last_save_time = time.time()
            self._clear_autosave()
            if show_feedback:
                self.bus.emit("saved", {"title": title, "success": True,
                                        "message": "保存成功", "path": str(filepath)})

        self._generate_chat_title(_on_title_ready)

    def _generate_chat_title(self, callback):
        """AI 生成对话标题（后台线程），完成后调用 callback(title)"""
        recent = self.app.history[-6:] if len(self.app.history) >= 4 else self.app.history[:]
        if not recent or not config.API_KEY:
            callback(self._fallback_chat_title())
            return

        prompt = self.app.ai.build_chat_title_prompt()

        def _on_title_result(content):
            result, err = extract_json(content)
            if result and result.get("title"):
                callback(result["title"].strip())
            else:
                print(f"[chat] 标题 JSON 提取失败: {err}")
                callback(self._fallback_chat_title())

        def _on_title_error(err):
            print(f"[chat] 标题 API 异常: {err}")
            callback(self._fallback_chat_title())

        call_chat_completion_async(
            messages=[
                {"role": "system", "content": "你是一个对话标题生成器，只返回JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=300,
            timeout=15.0,
            on_result=_on_title_result,
            on_error=_on_title_error,
        )

    # ── 读取 ──

    def load_chat(self, filepath) -> bool:
        """读取对话文件，恢复历史到 app 状态。
        返回 True 成功 / False 失败。UI 重建由调用方负责（监听 stopped 事件后重建）"""
        data = load_json(filepath)
        if not data or "history" not in data:
            return False

        app = self.app
        app.history = data.get("history", [])
        app.turn_idx = data.get("turn_idx", 0)
        app.turn_count = data.get("turn_count", 0)
        app.message_count = data.get("message_count", len(app.history))
        # 重建沉默追踪
        app._char_last_turn = {}
        for i, entry in enumerate(reversed(app.history)):
            name = entry.get("name", "")
            if name and name not in app._char_last_turn:
                app._char_last_turn[name] = app.turn_count - i
        app._suggested_next = None
        saved_scene = data.get("scene_idx", 0)
        if 0 <= saved_scene < len(app.scenes):
            app.scene_idx = saved_scene

        self._loaded_chat_path = filepath
        return True

    def delete_chat(self, filepath) -> bool:
        """删除对话文件"""
        try:
            filepath.unlink()
            return True
        except Exception as e:
            print(f"[chat] 删除失败: {e}")
            return False

    # ── 自动存档 ──

    def _auto_save(self):
        """暂停 / app 切后台时静默自动存档（不调 AI 标题）。"""
        if not self.app.history:
            return
        if len(self.app.history) == self._last_autosave_len:
            return  # 无变化，跳过
        self._ensure_chats_dir()
        if not self.chats_dir:
            return
        filepath = self.chats_dir / "_autosave.json"
        title = self._fallback_chat_title()
        self._save_chat_to_file(filepath, title)
        self._last_autosave_len = len(self.app.history)
        self._last_save_time = time.time()

    def _clear_autosave(self):
        """删除自动存档（用户已手动保存）"""
        if not self.chats_dir:
            return
        p = self.chats_dir / "_autosave.json"
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    def has_unsaved_messages(self) -> bool:
        """是否有未保存消息（30 秒内有新消息且未保存）"""
        return bool(self.app.history) and (time.time() - self._last_save_time > 30)

    def check_autosave_on_start(self):
        """启动时检测自动存档，有则发 "autosave_prompt" 事件让 UI 询问。"""
        if not self.chats_dir:
            return
        p = self.chats_dir / "_autosave.json"
        if not p.exists():
            return
        data = load_json(p)
        if not data or not data.get("history"):
            try:
                p.unlink()
            except Exception:
                pass
            return
        self.bus.emit("autosave_prompt", {
            "title": data.get("title", "自动存档"),
            "message_count": data.get("message_count", 0),
            "path": str(p),
        })

    def restore_autosave(self, path: str) -> bool:
        """用户选择恢复自动存档"""
        ok = self.load_chat(Path(path))
        if ok:
            self._clear_autosave()
        return ok

    def discard_autosave(self, path: str):
        """用户选择放弃自动存档"""
        try:
            Path(path).unlink()
        except Exception:
            pass
