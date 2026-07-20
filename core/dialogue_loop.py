# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 对话循环
  从 Kivy 版 main.py 的 _run_loop / _handle_cmd 抽出，零 UI 框架依赖。
  - 后台线程执行对话循环
  - 通过 EventBus 发送事件，UI 层订阅并更新控件
  - 命令（start/pause/resume/stop/reset/speed/mode）通过 set_command() 投递
  - 用户输入（导演提示 / 用户角色发言）通过 send_director_note() / send_user_message() 投递

  与 Kivy 版的核心差异：
  - 不再用 Queue + Clock 轮询，改为 EventBus 直发
  - 消息处理（[SCENE]/[NEXT] 剥离、history 追加、计数更新）从 _handle_cmd 移到此处
    （_handle_cmd 原本在主线程做，现在 loop 线程做，因为 Flet page.update 跨线程安全）
  - UI 更新（气泡渲染、状态栏）由 UI 层监听 bus 事件完成
"""

import random
import re
import threading
import time
from datetime import datetime
from typing import Optional

from core.events import EventBus
from services.api_service import APIError
import config


class DialogueLoop:
    """对话循环控制器。

    生命周期：
      start()   → 启动后台线程
      pause()   → 暂停（线程不退出，空转等待）
      resume()  → 恢复
      stop()    → 停止并清空（线程退出，状态重置）
      send_director_note(text)  → 注入导演提示
      send_user_message(text)   → 注入用户角色发言
    """

    def __init__(self, app):
        self.app = app
        self.bus: EventBus = app.bus
        self.ai = app.ai
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._paused = threading.Event()
        self._paused.set()  # 初始为暂停态（set=未暂停；clear=暂停）

        # 命令队列（用 threading.Event + 简单变量传速度/mode）
        # 简化：speed/mode 直接改 app 属性，pause/resume 用 Event
        # user_turn_wait: 当轮到用户时，用 Event 阻塞等待用户输入
        self._user_turn_event = threading.Event()
        self._user_input_text: Optional[str] = None
        self._user_input_skip = False
        self._waiting_for_user = False

    # ═══ 状态查询 ═══

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def paused(self) -> bool:
        return not self._paused.is_set()

    # ═══ 生命周期控制 ═══

    def start(self):
        """启动对话。若 scene_idx == -1（按时间生成），由 UI 层先调
        ai.generate_time_scene_sync() 并确认后再调此方法。"""
        from core.debug import invariant, validate_runtime_state
        # 允许在孤儿线程存活时调用（下方会等其退出），仅检查不应已有正常运行的线程
        if self._thread is not None and self._thread.is_alive():
            # 孤儿线程检测：stop() join 超时后线程可能仍活着（阻塞在网络 I/O）
            # 现已通过 stop_check 让流式 API 可被中断，但若孤儿线程仍存活，
            # 强制等其退出后再启动新线程，避免双 loop 并发。
            print("[loop] start: previous thread still alive, waiting for it to exit...")
            self._stop_event.set()
            self._thread.join(timeout=10.0)
            if self._thread.is_alive():
                print("[loop] start: orphan thread did not exit within 10s, aborting start")
                self.bus.emit("api_error_stop", "上轮对话未完全停止，请稍后重试")
                return
            self._thread = None
        else:
            if self._thread is not None:
                self._thread = None
        # 检查 API Key
        import config
        if not config.API_KEY:
            self.bus.emit("api_error_stop", "未配置 API Key，请在设置中填写")
            return

        # 初始化场景（动态模式从预设取首个场景）
        if self.app.dynamic_scene_enabled and self.app.scenes and not self.app.current_scene:
            s = self.app.scenes[self.app.scene_idx % len(self.app.scenes)]
            self.app.current_scene = {
                "time": s.get("time", ""), "location": s.get("location", ""),
                "scene": s.get("scene", ""), "mood": s.get("mood", ""),
            }
            self.app.scene_version = 0
            self.app._last_scene_update_turn = -1

        # 重置运行时状态
        self.app.running = True
        self.app.paused = False
        self.app._char_last_turn.clear()
        self.app._active_npc = None
        self.app._npc_silent_turns = 0
        self.app._npc_rounds_left = 0
        self.app._char_turns_since_event = 0
        self.ai._api_error_count = 0

        self._stop_event.clear()
        self._paused.set()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.bus.emit("started", None)
        self.bus.emit("set_status", "运行中")
        validate_runtime_state(self.app)

    def pause(self):
        """暂停对话（线程保持存活，空转等待）。"""
        from core.debug import invariant
        invariant(self.running, f"pause() 调用时 loop 未运行 (running={self.running})")
        if not self.running:
            return
        if self._waiting_for_user:
            return
        self.app.paused = True
        self._paused.clear()
        self.bus.emit("paused", None)
        self.bus.emit("set_status", "已暂停")
        # 暂停时自动存档
        self.app.chat._auto_save()
        # 导演模式开启时，UI 层监听 paused 事件显示输入栏

    def resume(self):
        """恢复对话。若暂停是因为轮到用户，需用户先输入再恢复。"""
        from core.debug import invariant
        invariant(self.running, f"resume() 调用时 loop 未运行 (running={self.running})")
        if not self.running:
            return
        if self._waiting_for_user:
            if "You" in self.app._get_effective_order():
                self.bus.emit("set_status", "请先输入发言或跳过")
                return
            self._waiting_for_user = False
            self._user_turn_event.set()
        self.app.paused = False
        self._paused.set()
        self.bus.emit("resumed", None)
        self.bus.emit("set_status", "运行中")

    def stop(self):
        """停止对话（线程退出，清空历史）。

        若从 loop 线程内部调用（如 API 错误），跳过 join 避免 RuntimeError。
        始终 emit "stopped" 事件，确保 UI 一致刷新。
        """
        from core.debug import invariant, validate_runtime_state
        self._stop_event.set()
        self._paused.set()  # 释放可能的暂停阻塞
        self._user_turn_event.set()  # 释放用户回合阻塞
        # 避免在 loop 线程内 join 自身（会抛 RuntimeError）
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=5.0)
        self._thread = None
        self.app.running = False
        self.app.paused = False
        # 清空对话历史与运行时状态（stop = 完全重置）
        with self.app._history_lock:
            self.app.history.clear()
        self.app.turn_idx = 0
        self.app.turn_count = 0
        self.app.message_count = 0
        self.app._char_last_turn.clear()
        self.app._suggested_next = None
        self.app._active_npc = None
        self.app._npc_silent_turns = 0
        self.app._npc_rounds_left = 0
        self.app._char_turns_since_event = 0
        self._waiting_for_user = False
        self.app.chat._loaded_chat_path = None
        self.app.chat._last_saved_count = -1  # 重置：下次有消息即视为未保存
        self.app.chat._last_autosave_len = 0
        self.app.chat._clear_autosave()  # 清除过期自动存档，避免下次启动弹出恢复提示
        self.bus.emit("stopped", None)
        validate_runtime_state(self.app)
        self.bus.emit("set_status", "已停止")

    def reset(self):
        """停止并清空对话历史（回到初始状态）。等同于 stop()。"""
        self.stop()

    def set_speed(self, speed: int):
        self.app.speed = max(1, min(10, speed))

    def set_mode(self, mode: str):
        """mode: 'round' | 'random' | 'dynamic'"""
        self.app.mode = mode
        self.app._char_last_turn.clear()
        self.app._suggested_next = None

    # ═══ 用户输入 ═══

    def send_director_note(self, text: str):
        """注入导演提示（直接追加到 history 并发事件）。"""
        text = text.strip()
        if not text:
            return
        entry = {
            "name": "__director__",
            "display_name": "导演",
            "text": text,
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": "director",
        }
        with self.app._history_lock:
            self.app.history.append(entry)
        self.bus.emit("msg", entry)

    def send_user_message(self, text: str):
        """注入用户角色发言（在用户回合时调用，解除阻塞）。"""
        text = text.strip()
        if not text:
            return
        self._waiting_for_user = False
        uc = self.app.characters.get("You", {})
        entry = {
            "name": "You",
            "display_name": uc.get("display_name", "你"),
            "text": text,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
        with self.app._history_lock:
            self.app.history.append(entry)
        self.app.turn_idx += 1
        self.app.turn_count += 1
        self.app._char_turns_since_event += 1
        self.app._char_last_turn["You"] = self.app.turn_count
        self.app._suggested_next = None
        self.app.message_count += 1
        self.bus.emit("msg", entry)
        # 解除用户回合阻塞
        self._user_input_text = text
        self._user_input_skip = False
        self._user_turn_event.set()

    def skip_user_turn(self):
        """用户跳过自己的回合。"""
        self._waiting_for_user = False
        self.app.turn_idx += 1
        self.app.turn_count += 1
        self._user_input_text = None
        self._user_input_skip = True
        self._user_turn_event.set()

    # ═══ 后台循环 ═══

    def _run(self):
        """对话主循环（后台线程）。"""
        # 按时间生成场景（scene_idx == -1 时在 loop 线程中生成，避免阻塞 UI）
        if self.app.scene_idx == -1 and not self.app.current_scene:
            self.bus.emit("set_status", "正在生成场景...")
            scene, err = self.ai.generate_time_scene_sync()
            if not self._stop_event.is_set() and scene:
                self.app.current_scene = scene
                self.app.scene_version += 1
                self.app._last_scene_update_turn = -1
                self.bus.emit("scene_changed", {
                    **scene, "version": self.app.scene_version,
                    "manual": True, "is_time_gen": True,
                })
            elif err and not self._stop_event.is_set():
                self.bus.emit("set_status", f"按时间生成场景失败: {err[:60]}")
                self.app.scene_idx = 0

        current_thread = threading.current_thread()
        _loop_iters = 0
        while not self._stop_event.is_set():
            try:
                # 周期性运行时状态检查（每 20 次迭代）
                _loop_iters += 1
                if _loop_iters % 20 == 0:
                    from core.debug import validate_runtime_state
                    validate_runtime_state(self.app)

                # 暂停态：空转等待
                self._paused.wait()
                if self._stop_event.is_set():
                    break

                # ═══ 随机事件 / NPC 注入（在角色发言前）═══
                if self.app.random_event_enabled:
                    if self._handle_npc_logic(current_thread):
                        continue
                    elif self._should_trigger_random():
                        self.bus.emit("set_status", "正在生成随机事件...")
                        result = self.ai._generate_random_event()
                        if self._stop_event.is_set():
                            break
                        if result:
                            self._emit_random_result(result)
                        else:
                            print("[random_event] generation failed, skipping")
                            self.app._char_turns_since_event = 0
                        self.bus.emit("set_status", "运行中")
                        time.sleep(0.2)
                        continue

                # ═══ 选发言人 ═══
                effective_order = self.app._get_effective_order()
                if not effective_order:
                    time.sleep(1)
                    continue

                if self.app.mode == "random":
                    name = random.choice(effective_order)
                elif self.app.mode == "dynamic":
                    name = self.ai._pick_next_speaker_rules()
                    if not name:
                        name = random.choice(effective_order)
                else:  # round
                    name = effective_order[self.app.turn_idx % len(effective_order)]

                # ═══ 用户回合 ═══
                if name == "You":
                    self._waiting_for_user = True
                    self.app.paused = True
                    self._paused.clear()
                    self.bus.emit("user_turn", None)
                    self.bus.emit("set_status", "轮到你了～")
                    self._user_turn_event.wait()
                    self._user_turn_event.clear()
                    if self._stop_event.is_set():
                        break
                    self.app.paused = False
                    self._paused.set()
                    self.bus.emit("resumed", None)
                    self.bus.emit("set_status", "运行中")
                    continue

                # ═══ 调 LLM ═══
                st = self.app.char_styles.get(name, {})
                dname = st.get("name", name)

                use_streaming = config.STREAMING_ENABLED

                if use_streaming:
                    # ── 流式路径 ──
                    msg_id = f"{name}_{self.app.turn_count}"
                    entry = {
                        "name": name,
                        "display_name": dname,
                        "text": "",
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "streaming": True,
                        "msg_id": msg_id,
                    }
                    with self.app._history_lock:
                        self.app.history.append(entry)
                    self.app.turn_idx += 1
                    self.app.turn_count += 1
                    self.app._char_turns_since_event += 1
                    if name and name != "You":
                        self.app._char_last_turn[name] = self.app.turn_count
                    self.app.message_count += 1

                    # 发初始气泡
                    self.bus.emit("msg", dict(entry))

                    raw_buf = []
                    last_flush = 0.0

                    def on_token(tok):
                        nonlocal last_flush
                        raw_buf.append(tok)
                        raw_text = "".join(raw_buf)
                        entry["text"] = raw_text
                        now = time.time()
                        if "\n" in tok or (now - last_flush) > 0.08:
                            self.bus.emit("msg_delta", dict(entry))
                            last_flush = now

                    text = ""
                    try:
                        reply, error = self.ai._call_llm_stream(name, on_token)

                        if self._stop_event.is_set():
                            break

                        if error:
                            if error.startswith("api_error_stop:"):
                                err_msg = error.split(":", 1)[1]
                                self.bus.emit("api_error_stop", err_msg)
                                self.stop()
                                return
                            self.bus.emit("set_status", f"API 错误: {error}")

                        # 解析 [SCENE] / [NEXT] 标签
                        text = reply
                        if self.app.dynamic_scene_enabled:
                            text, scene_dict = self.ai._parse_and_strip_scene_tag(text)
                            if scene_dict:
                                self._apply_scene_update(scene_dict)

                        text, next_name = self.ai._parse_and_strip_next_tag(text)
                        if next_name and next_name in self.app._get_effective_order():
                            self.app._suggested_next = next_name
                        else:
                            self.app._suggested_next = None

                        text = text.strip()
                    finally:
                        entry["streaming"] = False
                        if text:
                            entry["text"] = text
                        self.bus.emit("msg_end", dict(entry))

                else:
                    # ── 非流式路径（原有逻辑）──
                    reply, error = self.ai._call_llm(name)

                    if self._stop_event.is_set():
                        break

                    if error:
                        if error.startswith("api_error_stop:"):
                            err_msg = error.split(":", 1)[1]
                            self.bus.emit("api_error_stop", err_msg)
                            self.stop()
                            return
                        self.bus.emit("set_status", f"API 错误: {error}")

                    # 解析 [SCENE] / [NEXT] 标签
                    text = reply
                    if self.app.dynamic_scene_enabled:
                        text, scene_dict = self.ai._parse_and_strip_scene_tag(text)
                        if scene_dict:
                            self._apply_scene_update(scene_dict)

                    text, next_name = self.ai._parse_and_strip_next_tag(text)
                    if next_name and next_name in self.app._get_effective_order():
                        self.app._suggested_next = next_name
                    else:
                        self.app._suggested_next = None

                    entry = {
                        "name": name,
                        "display_name": dname,
                        "text": text.strip(),
                        "time": datetime.now().strftime("%H:%M:%S"),
                    }
                    with self.app._history_lock:
                        self.app.history.append(entry)
                    self.app.turn_idx += 1
                    self.app.turn_count += 1
                    self.app._char_turns_since_event += 1
                    if name and name != "You":
                        self.app._char_last_turn[name] = self.app.turn_count
                    self.app.message_count += 1
                    self.bus.emit("msg", entry)

                # 等待（速度控制），每 0.1s 检查暂停
                total = self.app.speed * 0.1
                elapsed = 0.0
                while elapsed < total and not self._stop_event.is_set():
                    self._paused.wait(0.1)
                    if not self._paused.is_set():
                        break
                    elapsed += 0.1

            except Exception as e:
                print(f"[loop] 异常: {e}")
                time.sleep(0.5)

    # ═══ 随机事件辅助 ═══

    def _stream_npc_dialogue(self, npc_name: str, generate_fn, is_farewell: bool = False,
                             post_process=None):
        """通用 NPC 流式对话发射。
        generate_fn(on_token) → 返回完整文本；post_process(text) → 返回处理后文本。
        使用 msg_delta/msg_end 事件复用现有 UI 流式更新管线。"""
        msg_id = f"npc_{npc_name}_{self.app.turn_count}"
        entry = {
            "name": "__random__",
            "display_name": npc_name,
            "text": "",
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": "random_npc",
            "streaming": True,
            "msg_id": msg_id,
        }
        if is_farewell:
            entry["is_farewell"] = True

        with self.app._history_lock:
            self.app.history.append(entry)
        self.app.turn_count += 1
        self.app.message_count += 1
        self.bus.emit("random_npc_msg", dict(entry))

        raw_buf = []
        last_flush = 0.0

        def on_token(tok):
            nonlocal last_flush
            raw_buf.append(tok)
            raw_text = "".join(raw_buf)
            entry["text"] = raw_text
            now = time.time()
            if "\n" in tok or (now - last_flush) > 0.08:
                self.bus.emit("msg_delta", dict(entry))
                last_flush = now

        response = ""
        try:
            response = generate_fn(on_token)
        except Exception as ex:
            print(f"[loop] _stream_npc_dialogue generate_fn error: {ex}")

        try:
            if self._stop_event.is_set():
                entry["streaming"] = False
                self.bus.emit("msg_end", dict(entry))
                # farewell 清理由 finally 统一处理
                return response

            if post_process:
                response = post_process(response)

            entry["text"] = (response or "").strip()
            entry["streaming"] = False
            self.bus.emit("msg_end", dict(entry))
        except Exception as ex:
            # post_process 抛异常或其他错误：仍保证 msg_end 触发，避免气泡永久停留流式态
            print(f"[loop] _stream_npc_dialogue post-process error: {ex}")
            entry["streaming"] = False
            if not entry.get("text"):
                entry["text"] = (response or "").strip()
            self.bus.emit("msg_end", dict(entry))
        finally:
            # farewell 清理必须执行：无论正常/异常/stop 路径，is_farewell 都要清空 _active_npc
            # 否则 NPC 状态机卡死，_should_trigger_random 持续返回 False 抑制随机事件
            if is_farewell:
                self.app._active_npc = None
                self.app._char_turns_since_event = 0

        return response

    def _handle_npc_logic(self, current_thread) -> bool:
        """处理活跃 NPC 的回应/沉默离开逻辑。
        返回 True 表示已处理并 continue 循环；False 表示无 NPC 或未触发。"""
        if self.app._active_npc is None:
            return False

        try:
            last_msg = self.app.history[-1] if self.app.history else None
        except IndexError:
            last_msg = None
        last_text = last_msg.get("text", "") if last_msg else ""

        # 检测角色是否提到 NPC
        if (last_msg and last_msg.get("type") not in ("random_npc", "random_event", "director")
                and self.ai._npc_is_mentioned(last_text)):
            self.bus.emit("set_status", f"路人\"{self.app._active_npc['name']}\"正在回应...")
            self.app._npc_silent_turns = 0
            self.app._npc_rounds_left -= 1
            npc_name = self.app._active_npc["name"]
            npc_is_departing = self.app._npc_rounds_left <= 0
            if npc_is_departing:
                print(f"[random_npc] NPC '{npc_name}' rounds exhausted, departing")

            if config.STREAMING_ENABLED:
                def _departure_process(text):
                    if "离开" not in text:
                        return text + " *说完便转身离开了*"
                    return text

                self._stream_npc_dialogue(
                    npc_name,
                    self.ai._generate_npc_response_stream,
                    is_farewell=npc_is_departing,
                    post_process=_departure_process if npc_is_departing else None,
                )
                if self._stop_event.is_set():
                    return True
            else:
                response = self.ai._generate_npc_response()
                if self._stop_event.is_set():
                    return True
                if npc_is_departing:
                    if "离开" not in response:
                        response = response + " *说完便转身离开了*"
                entry = {
                    "name": "__random__",
                    "display_name": npc_name,
                    "text": response,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "type": "random_npc",
                }
                if npc_is_departing:
                    entry["is_farewell"] = True
                self._emit_npc_message(entry)
            if not self.paused:
                self.bus.emit("set_status", "运行中")
            time.sleep(0.15)
            return True

        # 未提及 → 累积沉默
        elif last_msg and last_msg.get("type") not in ("random_npc", "random_event", "director"):
            self.app._npc_silent_turns += 1
            print(f"[random_npc] not mentioned ({self.app._npc_silent_turns}/4)")
            if self.app._npc_silent_turns >= 4:
                npc_name = self.app._active_npc["name"]
                print(f"[random_npc] '{npc_name}' left (silent too long)")
                entry = {
                    "name": "__random__",
                    "display_name": npc_name,
                    "text": f"*{npc_name} 见没人理会，默默离开了*",
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "type": "random_npc",
                    "is_farewell": True,
                }
                self._emit_npc_message(entry)
                if not self.paused:
                    self.bus.emit("set_status", "运行中")
                time.sleep(0.15)
                return True
        return False

    def _should_trigger_random(self) -> bool:
        return self.ai._should_trigger_random()

    def _emit_random_result(self, result: dict):
        """将 AI 生成的随机事件/NPC 结果发送到 UI。"""
        if result.get("type") == "npc":
            npc_name = result.get("name", "路人")
            npc_desc = result.get("desc", "")
            self.app._active_npc = {"name": npc_name, "desc": npc_desc}
            self.app._npc_rounds_left = 2
            self.app._npc_silent_turns = 0
            print(f"[random_npc] introduced: '{npc_name}' rounds_left=2")

            if config.STREAMING_ENABLED:
                self._stream_npc_dialogue(
                    npc_name,
                    self.ai._generate_npc_intro_stream,
                    is_farewell=False,
                )
                if self._stop_event.is_set():
                    return
            else:
                dialogue = result.get("dialogue", "")
                entry = {
                    "name": "__random__",
                    "display_name": npc_name,
                    "text": dialogue,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "type": "random_npc",
                }
                self._emit_npc_message(entry)
        else:
            event_text = result.get("text", "")
            self.app._char_turns_since_event = 0
            entry = {
                "name": "__random__",
                "display_name": "随机事件",
                "text": event_text,
                "time": datetime.now().strftime("%H:%M:%S"),
                "type": "random_event",
            }
            with self.app._history_lock:
                self.app.history.append(entry)
            self.app.turn_count += 1
            self.app.message_count += 1
            self.bus.emit("random_event_msg", entry)

    def _emit_npc_message(self, entry: dict):
        """发送 NPC 消息并更新 history/计数。"""
        with self.app._history_lock:
            self.app.history.append(entry)
        self.app.turn_count += 1
        self.app.message_count += 1
        self.bus.emit("random_npc_msg", entry)
        if entry.get("is_farewell"):
            self.app._active_npc = None
            self.app._char_turns_since_event = 0

    def _apply_scene_update(self, scene_dict: dict):
        """应用场景切换（来自 [SCENE] 标签）。"""
        if not self.app.current_scene:
            self.app.current_scene = {}
        # 合并：time/location 有则覆盖，scene 必覆盖
        if scene_dict.get("time"):
            self.app.current_scene["time"] = scene_dict["time"]
        if scene_dict.get("location"):
            self.app.current_scene["location"] = scene_dict["location"]
        if scene_dict.get("scene"):
            self.app.current_scene["scene"] = scene_dict["scene"]
        if "mood" in scene_dict:
            self.app.current_scene["mood"] = scene_dict["mood"]
        self.app.scene_version += 1
        self.app._last_scene_update_turn = self.app.turn_count
        print(f"[scene] v{self.app.scene_version - 1} -> v{self.app.scene_version}: "
              f"{self.app.current_scene.get('time', '')}|{self.app.current_scene.get('location', '')}")
        self.bus.emit("scene_changed", {
            "time": self.app.current_scene.get("time", ""),
            "location": self.app.current_scene.get("location", ""),
            "scene": self.app.current_scene.get("scene", ""),
            "mood": self.app.current_scene.get("mood", ""),
            "version": self.app.scene_version,
        })

    # ═══ 场景手动切换（UI 调用）═══

    def prev_scene(self):
        """上一个场景（含"按时间生成"位 -1）。"""
        n = len(self.app.scenes) if self.app.scenes else 0
        if n == 0:
            return
        if self.app.scene_idx == -1:
            self.app.scene_idx = n - 1 if n > 0 else 0
        elif self.app.scene_idx == 0:
            self.app.scene_idx = -1
        else:
            self.app.scene_idx -= 1
        self._on_manual_scene_switch()

    def next_scene(self):
        n = len(self.app.scenes) if self.app.scenes else 0
        if n == 0:
            return
        if self.app.scene_idx == -1:
            self.app.scene_idx = 0
        elif self.app.scene_idx == n - 1:
            self.app.scene_idx = -1
        else:
            self.app.scene_idx += 1
        self._on_manual_scene_switch()

    def _on_manual_scene_switch(self):
        if self.app.scene_idx == -1:
            print("[scene] switched to: 按时间")
        elif self.app.dynamic_scene_enabled and self.app.running and self.app.scenes:
            s = self.app.scenes[self.app.scene_idx % len(self.app.scenes)]
            self.app.current_scene = {
                "time": s.get("time", ""), "location": s.get("location", ""),
                "scene": s.get("scene", ""), "mood": s.get("mood", ""),
            }
            self.app.scene_version += 1
            self.app._last_scene_update_turn = self.app.turn_count
        self.bus.emit("scene_changed", {
            "time": (self.app.current_scene or {}).get("time", ""),
            "location": (self.app.current_scene or {}).get("location", ""),
            "scene": (self.app.current_scene or {}).get("scene", ""),
            "mood": (self.app.current_scene or {}).get("mood", ""),
            "version": self.app.scene_version,
            "manual": True,
            "is_time_gen": self.app.scene_idx == -1,
        })
