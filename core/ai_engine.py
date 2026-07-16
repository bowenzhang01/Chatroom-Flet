# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · AI 引擎
  迁移自 Kivy 版 core/ai_engine.py，零 UI 框架依赖。
  - 移除 self.app._set_status / self.app._queue.put（改由 DialogueLoop 通过 EventBus 通知）
  - 移除 self.app._api_error_count 的 UI 联动（错误计数仍保留，停止事件由 loop 发出）
  - 保留：prompt 构建 / 动态发言人选择 / 随机事件 / 路人 NPC 全部逻辑
  - 随机事件参数改用 config.RANDOM_EVENT_DEFAULTS（用户不可调）

  核心方法：
    _build_prompt(name)              → 构建角色 prompt（含场景/历史/输出提示）
    _call_llm(name)                  → 调 LLM 生成角色发言，返回 (text, error_or_None)
    _pick_next_speaker_rules()       → 动态模式加权选人
    _should_trigger_random()         → 随机事件概率判定
    _generate_random_event()         → 生成事件/NPC，返回 dict 或 None
    _generate_npc_response()         → 生成 NPC 回应
    _parse_and_strip_scene_tag(text) → 解析 [SCENE]...[/SCENE] 并返回 (clean_text, scene_or_None)
    _parse_and_strip_next_tag(text)  → 解析 [NEXT:Name] 并返回 (clean_text, next_name_or_None)
"""

import json
import random
import re
from datetime import datetime

from services.api_service import call_chat_completion, APIError
from utils import extract_json
import config


class AIEngine:
    """AI 对话引擎 — 通过 app 引用读取状态，不直接操作 UI。"""

    def __init__(self, app):
        self.app = app
        self._api_error_count = 0  # 连续失败计数

    # ═══ 场景与 Prompt 构建 ═══

    def _get_scene_text(self) -> str:
        """构建当前场景文本（供 prompt 使用）。
        优先级：动态 current_scene > 静态 scenes[scene_idx] > 空"""
        if self.app.current_scene and (self.app.dynamic_scene_enabled or self.app.scene_idx == -1):
            s = self.app.current_scene
            src = "dynamic"
        elif self.app.scenes:
            s = self.app.scenes[self.app.scene_idx % len(self.app.scenes)]
            src = "static"
        else:
            s = {"time": "", "scene": "", "location": ""}
            src = "empty"
        loc = f"地点：{s.get('location', '')}。" if s.get('location', '') else ""
        result = f"{s.get('time', '')}。{loc}{s.get('scene', '')}"
        print(f"[scene] prompt source={src}: {result[:80]}...")
        return result

    def _build_prompt(self, name: str) -> str:
        """构建角色发言 prompt。"""
        char = self.app.characters.get(name, {})
        scene = self._get_scene_text()
        recent = self.app.history[-8:] if self.app.history else []
        lines = []
        for m in recent:
            if m.get("type") == "director":
                lines.append(f" [Director's note - incorporate this into the scene]: {m['text']}")
            elif m.get("type") == "random_event":
                lines.append(f" [Something happened in the environment]: {m['text']}")
            elif m.get("type") == "random_npc":
                npc_name = m.get("display_name", "路人")
                lines.append(f"[Passerby {npc_name} says]: {m['text']}")
            else:
                dname = m.get("display_name", m["name"])
                lines.append(f"{dname}: {m['text']}")
        dialogue = "\n\n".join(lines) if lines else "(Just arrived)"

        # 用户模式注入提示
        user_note = ""
        if self.app.user_mode and "You" in self.app.characters:
            uc = self.app.characters["You"]
            dname = uc.get('display_name', '你')
            desc = uc.get('description', '一个普通人')
            pers = uc.get('personality', '')
            pers_line = f"性格{pers}。" if pers else ""
            user_note = (
                f"\n\n{dname}也在场——{desc}。{pers_line}"
                f"和其他角色一样对待，自然地与{dname}对话、互动。"
            )

        return (
            f"{scene}{user_note}\n\n[Recent]\n{dialogue}\n\n"
            f"[Your turn - {char.get('display_name', name)}]\n"
            f"Respond naturally. Describe what you do."
            + self._build_output_hints(name)
        )

    def _build_output_hints(self, current_speaker: str) -> str:
        """动态模式追加 [NEXT] 提示；动态场景追加 [SCENE] 提示。"""
        parts = []

        if self.app.mode == "dynamic":
            others = [n for n in self.app._get_effective_order() if n != current_speaker]
            if others:
                other_names = ", ".join(others)
                parts.append(
                    f"\n\nOn the very last line of your reply ONLY, add [NEXT:Name] "
                    f"to suggest who should speak next. Pick from: {other_names}. "
                    f"Do NOT include [NEXT] inside your dialogue or actions."
                )

        if self.app.dynamic_scene_enabled:
            parts.append(
                f"\n\nIf the physical environment, time, weather, or location has visibly "
                f"changed in your turn, optionally describe the new scene on your very last line:\n"
                f"[SCENE]time。地点：location。description[/SCENE]\n"
                f"Use the same format as the scene description above. "
                f"Only include this if the scene actually changed."
            )

        return "".join(parts)

    # ═══ LLM 调用 ═══

    def _call_llm(self, name: str):
        """调 LLM 生成角色发言。
        返回 (text, error_or_None)。成功时 error 为 None；
        失败时 text 为占位文本，error 为错误消息。
        连续失败 ≥3 次时，error 标记为 'api_error_stop' 触发停止。"""
        char = self.app.characters.get(name)
        if not char:
            return ("...", "角色不存在")
        prompt = self._build_prompt(name)
        try:
            content = call_chat_completion(
                messages=[
                    {"role": "system", "content": char["system_prompt"]},
                    {"role": "user", "content": prompt},
                ],
            )
            self._api_error_count = 0
            return (content, None)
        except APIError as e:
            self._api_error_count += 1
            err_msg = str(e)
            print(f"[ai_engine] LLM 错误 ({self._api_error_count}/3): {err_msg}")
            if self._api_error_count >= 3:
                self._api_error_count = 0
                return (f"*{name} 遇到了问题*", "api_error_stop:" + err_msg)
            return (f"*{name} thought for a moment*", err_msg)

    # ═══ 动态发言人选择 ═══

    def _pick_next_speaker_rules(self):
        """规则加权随机选人。零 API 成本。
        因子：沉默惩罚 / 直接点名 / 反自说自话 / [NEXT] 提示。
        返回角色 name 或 None（仅 1 人时）。"""
        effective_order = self.app._get_effective_order()
        if not effective_order or len(effective_order) <= 1:
            return None

        # 硬兜底：15 轮沉默强制插入（用户 12 轮）
        HARD_SILENCE = 15
        USER_HARD_SILENCE = 12
        for name in effective_order:
            last = self.app._char_last_turn.get(name, -1)
            silence = self.app.turn_count if last < 0 else self.app.turn_count - last
            limit = USER_HARD_SILENCE if name == "You" else HARD_SILENCE
            if silence >= limit:
                print(f"[director] hard silence: {name} ({silence} turns)")
                return name

        # 上下文
        last_speaker = None
        last_text = ""
        if self.app.history:
            last_msg = self.app.history[-1]
            last_speaker = last_msg.get("name", "")
            last_text = last_msg.get("text", "")

        if self.app._suggested_next:
            print(f"[director] hint from prev char: {self.app._suggested_next}")

        # 计算权重
        weights = {}
        total = 0.0
        for name in effective_order:
            w = 1.0
            factors = []

            # A: 沉默惩罚（用户 0.6× 衰减）
            last = self.app._char_last_turn.get(name, -1)
            silence = self.app.turn_count if last < 0 else self.app.turn_count - last
            sil_bonus = min(silence, 10) * 0.25
            if name == "You":
                sil_bonus *= 0.6
            w += sil_bonus
            if sil_bonus > 0:
                factors.append(f"silence+{sil_bonus:.1f}")

            # B: 直接点名（×3.0）
            if last_text and name in last_text:
                w *= 3.0
                factors.append("mentioned")

            # C: 反自说自话（×0.1）
            if name == last_speaker:
                w *= 0.1
                factors.append("self")

            # D: [NEXT] 提示（×5.0）
            if name == self.app._suggested_next:
                w *= 5.0
                factors.append("hint")

            weights[name] = (w, factors)
            total += w

        if total <= 0:
            picked = random.choice(effective_order)
            print(f"[director] zero weights -> random: {picked}")
            return picked

        # 加权随机
        r = random.random() * total
        cumulative = 0.0
        picked = effective_order[-1]
        for name in effective_order:
            w, factors = weights[name]
            pct = w / total * 100
            factor_str = ", ".join(factors) if factors else "base"
            print(f"[director]   {name}: w={w:.2f} ({pct:.0f}%) [{factor_str}]")
            cumulative += w
            if r <= cumulative:
                picked = name
                break

        print(f"[director] picked: {picked}")
        return picked

    # ═══ 标签解析（[SCENE] / [NEXT]）═══

    def _parse_and_strip_scene_tag(self, text: str):
        """解析并剥离 [SCENE]...[/SCENE] 标签。
        返回 (clean_text, scene_dict_or_None)。"""
        scene_matches = list(re.finditer(r'\[SCENE\](.+?)\[/SCENE\]', text, re.DOTALL))
        if not scene_matches:
            return (text, None)
        m = scene_matches[-1]
        scene_content = m.group(1).strip()
        scene_dict = None
        if scene_content:
            scene_dict = self._parse_scene_content(scene_content)
            print(f"[scene] tag detected: {scene_content[:80]}...")
        # 剥离标签及周围空白
        start, end = m.start(), m.end()
        while start > 0 and text[start - 1] in (' ', '\n', '\r', '\t'):
            start -= 1
        while end < len(text) and text[end] in (' ', '\n', '\r', '\t'):
            end += 1
        clean = text[:start] + text[end:]
        return (clean, scene_dict)

    def _parse_scene_content(self, content: str) -> dict:
        """解析场景标签内容为 {time, location, scene} 字典。"""
        m = re.match(r'^(.+?)。地点：(.+?)。(.+)$', content)
        if m:
            return {
                "time": m.group(1).strip(),
                "location": m.group(2).strip(),
                "scene": m.group(3).strip(),
            }
        return {"time": "", "location": "", "scene": content}

    def _parse_and_strip_next_tag(self, text: str):
        """解析并剥离末尾的 [NEXT:Name] 标签。
        返回 (clean_text, next_name_or_None)。"""
        next_match = re.search(r'\[NEXT:([^\]]+)\]', text)
        if not next_match:
            return (text, None)
        next_name = next_match.group(1).strip()
        # 仅剥离位于末尾的 [NEXT]
        clean = re.sub(r'\s*\[NEXT:[^\]]+\]\s*$', '', text).strip()
        return (clean, next_name)

    # ═══ 随机事件 / NPC 引擎 ═══

    def _should_trigger_random(self) -> bool:
        """概率斜坡判定是否触发随机事件。参数用 config.RANDOM_EVENT_DEFAULTS。"""
        if not self.app.random_event_enabled:
            return False
        if self.app._active_npc is not None:
            return False
        rc = config.RANDOM_EVENT_DEFAULTS
        min_cooldown = rc["min_cooldown"]
        ramp_length = rc["ramp_length"]
        max_prob = rc["max_probability"]
        turns_since = self.app._char_turns_since_event
        if turns_since < min_cooldown:
            prob = 0.0
        elif turns_since < min_cooldown + ramp_length:
            prob = max_prob * (turns_since - min_cooldown) / ramp_length
        else:
            prob = max_prob
        roll = random.random()
        print(f"[random_event] turns_since={turns_since} p={prob:.3f} roll={roll:.3f} "
              f"trigger={roll < prob}")
        return roll < prob

    def _npc_is_mentioned(self, text: str) -> bool:
        if not self.app._active_npc:
            return False
        npc_name = self.app._active_npc.get("name", "")
        if not npc_name:
            return False
        if npc_name in text:
            print(f"[random_npc] NPC '{npc_name}' mentioned")
            return True
        return False

    def _build_random_event_prompt(self) -> str:
        world_config = self.app._profile_config.get("world", {})
        world_setting = world_config.get("setting", "") if world_config else ""
        world_line = f"【世界观】\n{world_setting}\n\n" if world_setting else ""
        scene = self._get_scene_text()
        char_names = []
        for name in self.app._get_effective_order():
            st = self.app.char_styles.get(name, {})
            dname = st.get("name", name)
            char_names.append(f"- {dname}")
        char_list = "\n".join(char_names) if char_names else "(无人)"

        event_weight = config.RANDOM_EVENT_DEFAULTS["event_weight"]
        type_hint = "事件" if random.random() < event_weight else "NPC"

        return (
            f"{world_line}"
            f"【当前场景】\n{scene}\n\n"
            f"【已在场的角色】\n{char_list}\n\n"
            f"请随机生成一个'{type_hint}'：\n\n"
            f"如果是'事件'：描述一个外部环境变化或突发事件（2-4句话）。"
            f"只涉及环境/外部因素，不涉及在场角色的具体行为。\n"
            f"如果是'NPC'：生成一个不在上述角色列表中的临时路人。"
            f"给出名字（2-4字中文）、一句话简介，以及一句符合身份的对话（20-40字）。\n\n"
            f"只返回纯JSON，不要```代码块：\n"
            f'事件: {{"type":"event","text":"..."}}\n'
            f'NPC: {{"type":"npc","name":"...","desc":"...","dialogue":"..."}}'
        )

    def _build_npc_response_prompt(self) -> str:
        npc = self.app._active_npc or {}
        npc_name = npc.get("name", "路人")
        npc_desc = npc.get("desc", "一个经过的路人")
        scene = self._get_scene_text()
        recent = self.app.history[-6:] if self.app.history else []
        lines = []
        for m in recent:
            dname = m.get("display_name", m["name"])
            if m.get("type") in ("director", "random_event"):
                continue
            lines.append(f"{dname}: {m['text']}")
        dialogue = "\n\n".join(lines) if lines else "(无人发言)"

        return (
            f"{scene}\n\n"
            f"[Recent]\n{dialogue}\n\n"
            f"[Your turn - {npc_name}]\n"
            f"你是一个路人: {npc_desc}。"
            f"自然地回应在场角色的对话。回复简短自然，50-100字。用*星号*描述动作和表情。"
            f"不要抢戏，说完你的事就可以准备离开了。"
        )

    def _generate_random_event(self):
        """生成随机事件/NPC。返回 dict 或 None。"""
        print("[random_event] generating...")
        prompt = self._build_random_event_prompt()
        try:
            content = call_chat_completion(
                messages=[
                    {"role": "system", "content": "你是场景事件/NPC生成器，只返回JSON。生成的事件或NPC应符合世界观和当前场景。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.9,
                max_tokens=300,
            )
            result, err = extract_json(content)
            if result:
                print(f"[random_event] AI returned: type={result.get('type')} "
                      f"text={result.get('text', result.get('dialogue', ''))[:60]}...")
                return result
            print(f"[random_event] JSON parse failed: {err}")
            return None
        except APIError as e:
            print(f"[random_event] API error: {e}")
            return None

    def _generate_npc_response(self):
        """生成路人 NPC 回应。返回文本或占位。"""
        npc = self.app._active_npc or {}
        npc_name = npc.get("name", "路人")
        print(f"[random_npc] generating response for '{npc_name}'...")
        prompt = self._build_npc_response_prompt()
        try:
            content = call_chat_completion(
                messages=[
                    {"role": "system", "content": (
                        f"你正在扮演一个临时路人角色：\"{npc_name}\"。"
                        f"{npc.get('desc', '一个路过的行人')}。"
                        f"自然地回应在场角色。回复简短自然，50-100字。用*星号*描述动作和表情。"
                    )},
                    {"role": "user", "content": prompt},
                ],
            )
            print(f"[random_npc] '{npc_name}' response: {content[:80]}...")
            return content
        except APIError as e:
            print(f"[random_npc] API error: {e}")
            return f"*{npc_name} 摆了摆手*"

    # ═══ 时间场景生成（scene_idx == -1 时调用）═══

    def _get_time_label(self) -> str:
        """系统小时 → 中文时段标签。"""
        hour = datetime.now().hour
        if 5 <= hour < 8:
            return "清晨"
        elif 8 <= hour < 12:
            return "上午"
        elif 12 <= hour < 14:
            return "中午"
        elif 14 <= hour < 17:
            return "午后"
        elif 17 <= hour < 19:
            return "傍晚"
        elif 19 <= hour < 22:
            return "晚上"
        elif 22 <= hour < 24 or 0 <= hour < 2:
            return "深夜"
        else:
            return "凌晨"

    def build_time_scene_prompt(self) -> str:
        """构建按现实时间生成场景的 prompt（供 DialogueLoop 在 scene_idx==-1 时调用）。"""
        label = self._get_time_label()
        now = datetime.now()
        wc = self.app._profile_config.get("world", {})
        world_setting = wc.get("setting", "") if wc else ""
        world_line = f"【世界观】\n{world_setting}\n\n" if world_setting else ""
        return (
            f"{world_line}"
            f"【当前现实时间】\n"
            f"{label} {now.hour:02d}:{now.minute:02d}\n\n"
            f"请你作为场景设计师，根据当前现实时间和世界观，创建一个合适的场景。\n\n"
            f"要求：\n"
            f"- time: 时间标签，用\"{label}\"或相近的简洁表达，2-6字\n"
            f"- location: 符合世界观的具体地点名称，2-6字\n"
            f"- mood: 氛围标签，2-4字\n"
            f"- scene: 场景描述，80-150字，像小说段落。必须包含光线、声音、气味中至少两种感官描写\n\n"
            f"【输出格式】只返回纯JSON，不要```代码块：\n"
            f'{{"time":"...","location":"...","mood":"...","scene":"..."}}'
        )

    def generate_time_scene_sync(self):
        """同步调用 LLM 生成时间场景。返回 (scene_dict_or_None, error_or_None)。"""
        prompt = self.build_time_scene_prompt()
        try:
            content = call_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                api_key=config.resolve_key(),
                temperature=0.8,
                max_tokens=500,
            )
            result, err = extract_json(content)
            if result:
                return (result, None)
            return (None, err or "场景 JSON 解析失败")
        except APIError as e:
            return (None, str(e))

    # ═══ 对话标题生成（供 ChatManager 调用）═══

    def build_chat_title_prompt(self) -> str:
        """构建对话标题生成 prompt。"""
        recent = self.app.history[-6:] if len(self.app.history) >= 4 else self.app.history[:]
        lines = []
        for m in recent:
            name = m.get("display_name", m.get("name", "?"))
            txt = m.get("text", "")[:80]
            lines.append(f"{name}: {txt}")
        lines_str = "\n".join(lines)
        return (
            f"根据以下对话片段，生成一个简短标题（5-15字），概括这段对话的主题。\n\n"
            f"{lines_str}\n\n"
            f"返回纯JSON：{{\"title\":\"标题\"}}"
        )

    # ═══ AI 一键创建剧本 ═══

    def build_profile_generation_prompt(self, description: str) -> str:
        """构建「一键创建剧本」prompt：从描述生成世界/场景/角色。"""
        return (
            "你是一个 RPG 剧本设计师。根据用户的描述，设计一个 ChatRoom 角色扮演剧本。\n\n"
            f"用户描述：{description}\n\n"
            "要求：\n"
            "1. 生成 3-5 个有性格差异的角色（含名字、英文名、性格、外貌描述、system_prompt）\n"
            "2. 生成 3-6 个场景（时间、地点、场景描述、氛围）\n"
            "3. 给出世界观设定（1-2 句）\n"
            "4. system_prompt 要详细定义角色人设、语气、表达方式，对话用「」包裹，动作用*星号*\n"
            "5. 必须包含一个名为\"You\"的用户角色（display_name:\"你\"），代表玩家操控的角色。\n"
            "   为用户角色设定适合该世界的性格、外貌描述和背景，让玩家有代入感。\n\n"
            "返回纯 JSON，结构如下：\n"
            '{"title":"剧本标题","world":"世界观","scenes":['
            '{"time":"清晨","location":"地点","scene":"描述","mood":"氛围"}],'
            '"characters":[{"name":"Yuki","display_name":"小雪","color":"#7ec8e3",'
            '"description":"描述","personality":"性格","system_prompt":"详细人设"},'
            '{"name":"You","display_name":"你","color":"#42a5f5",'
            '"description":"描述","personality":"性格","system_prompt":"用户角色人设"}],'
            '"turn_order":["Yuki","Rui","You"]}\n'
            "只返回 JSON，不要其他文字。"
        )

    def generate_profile_async(self, description: str, on_result, on_error=None):
        """异步生成完整剧本。on_result(parsed_dict) / on_error(msg)。

        parsed_dict: {title, world, scenes:[...], characters:[...], turn_order:[...]}
        """
        from services.api_service import call_chat_completion_async
        if not config.API_KEY:
            if on_error:
                on_error("未配置 API Key")
            return

        prompt = self.build_profile_generation_prompt(description)

        def _on_text(content):
            try:
                data, err = extract_json(content)
                if not data:
                    if on_error:
                        on_error(f"解析失败: {err}")
                    return
                # 基本校验
                if not data.get("characters") or not data.get("scenes"):
                    if on_error:
                        on_error("返回数据缺少角色或场景")
                    return
                on_result(data)
            except Exception as ex:
                if on_error:
                    on_error(str(ex))

        call_chat_completion_async(
            messages=[
                {"role": "system", "content": "你是一个剧本设计师，只返回JSON。"},
                {"role": "user", "content": prompt},
            ],
            on_result=_on_text,
            on_error=on_error,
            temperature=0.9,
            max_tokens=2500,
            timeout=60.0,
        )

    # ═══ AI 生成场景 / 角色 / 推断世界观 / 补全角色 ═══

    def build_generate_scenes_prompt(self) -> str:
        """构建「AI 生成场景」prompt：根据世界观和角色生成场景列表。"""
        world = self.app._profile_config.get("world", {}).get("setting", "")
        world_line = f"【世界观】\n{world}\n\n" if world else ""
        char_lines = []
        for name, c in self.app.characters.items():
            dname = c.get("display_name", name)
            desc = c.get("description", "") or c.get("personality", "")
            char_lines.append(f"- {dname}: {desc[:40]}")
        char_list = "\n".join(char_lines) if char_lines else "(暂无角色)"
        existing = self.app.scenes or []
        existing_lines = [f"- {s.get('time','')}·{s.get('location','')}" for s in existing]
        existing_str = "\n".join(existing_lines) if existing_lines else "(无)"

        return (
            f"{world_line}"
            f"【已有角色】\n{char_list}\n\n"
            f"【已有场景（避免重复）】\n{existing_str}\n\n"
            f"请为这个剧本生成 3-6 个新场景。每个场景包含：\n"
            f"- time: 时间标签（2-6字，如「清晨」「午后」「深夜」）\n"
            f"- location: 地点名称（2-6字）\n"
            f"- mood: 氛围（2-4字）\n"
            f"- scene: 场景描述（80-150字，像小说段落，含感官描写）\n\n"
            f"返回纯JSON数组，不要```代码块：\n"
            f'[{{"time":"...","location":"...","mood":"...","scene":"..."}}]'
        )

    def generate_scenes_async(self, on_result, on_error=None):
        """异步生成场景列表。on_result(scenes_list) / on_error(msg)。"""
        from services.api_service import call_chat_completion_async
        if not config.API_KEY:
            if on_error:
                on_error("未配置 API Key")
            return

        prompt = self.build_generate_scenes_prompt()

        def _on_text(content):
            try:
                data, err = extract_json(content)
                if not data:
                    if on_error:
                        on_error(f"解析失败: {err}")
                    return
                # 兼容：AI 可能返回 {"scenes": [...]} 而非纯数组
                if isinstance(data, dict):
                    for k in ("scenes", "data", "items", "results"):
                        if isinstance(data.get(k), list):
                            data = data[k]
                            break
                if not isinstance(data, list):
                    if on_error:
                        on_error("返回数据不是场景列表")
                    return
                on_result(data)
            except Exception as ex:
                if on_error:
                    on_error(str(ex))

        call_chat_completion_async(
            messages=[
                {"role": "system", "content": "你是场景设计师，只返回JSON数组。"},
                {"role": "user", "content": prompt},
            ],
            on_result=_on_text,
            on_error=on_error,
            temperature=0.85,
            max_tokens=1500,
            timeout=45.0,
        )

    def build_generate_characters_prompt(self) -> str:
        """构建「AI 生成角色」prompt：根据世界观和场景生成角色列表。"""
        world = self.app._profile_config.get("world", {}).get("setting", "")
        world_line = f"【世界观】\n{world}\n\n" if world else ""
        scene_lines = [f"- {s.get('time','')}·{s.get('location','')}: {s.get('scene','')[:40]}"
                       for s in (self.app.scenes or [])]
        scene_list = "\n".join(scene_lines) if scene_lines else "(暂无场景)"
        existing = [c.get("display_name", name) for name, c in self.app.characters.items()]
        existing_str = "、".join(existing) if existing else "(无)"

        return (
            f"{world_line}"
            f"【已有场景】\n{scene_list}\n\n"
            f"【已有角色（避免重复）】\n{existing_str}\n\n"
            f"请为这个剧本生成 3-5 个新角色。要求：\n"
            f"1. 名字（name: 英文）和显示名（display_name: 中文）\n"
            f"2. 性格有差异，互补或冲突\n"
            f"3. color: 用 #RRGGBB 格式，每个角色不同色调\n"
            f"4. description: 外貌+身份描述（30-60字）\n"
            f"5. personality: 性格关键词（10-20字）\n"
            f"6. system_prompt: 详细人设定义，包括语气、表达方式、口头禅等\n"
            f"   对话用「」包裹，动作用*星号*描述\n\n"
            f"返回纯JSON数组，不要```代码块：\n"
            f'[{{"name":"Yuki","display_name":"小雪","color":"#7ec8e3",'
            f'"description":"...","personality":"...","system_prompt":"..."}}]'
        )

    def generate_characters_async(self, on_result, on_error=None):
        """异步生成角色列表。on_result(characters_list) / on_error(msg)。"""
        from services.api_service import call_chat_completion_async
        if not config.API_KEY:
            if on_error:
                on_error("未配置 API Key")
            return

        prompt = self.build_generate_characters_prompt()

        def _on_text(content):
            try:
                data, err = extract_json(content)
                if not data:
                    if on_error:
                        on_error(f"解析失败: {err}")
                    return
                # 兼容：AI 可能返回 {"characters": [...]} 而非纯数组
                if isinstance(data, dict):
                    for k in ("characters", "data", "items", "results"):
                        if isinstance(data.get(k), list):
                            data = data[k]
                            break
                if not isinstance(data, list):
                    if on_error:
                        on_error("返回数据不是角色列表")
                    return
                on_result(data)
            except Exception as ex:
                if on_error:
                    on_error(str(ex))

        call_chat_completion_async(
            messages=[
                {"role": "system", "content": "你是角色设计师，只返回JSON数组。"},
                {"role": "user", "content": prompt},
            ],
            on_result=_on_text,
            on_error=on_error,
            temperature=0.9,
            max_tokens=2500,
            timeout=60.0,
        )

    def build_complete_character_prompt(self, char_name: str) -> str:
        """构建「补全角色」prompt：为已有角色填充缺失字段。"""
        c = self.app.characters.get(char_name, {})
        world = self.app._profile_config.get("world", {}).get("setting", "")
        world_line = f"【世界观】\n{world}\n\n" if world else ""
        existing_fields = {k: v for k, v in c.items() if k not in ("bg_color",)}
        fields_str = json.dumps(existing_fields, ensure_ascii=False, indent=2)

        return (
            f"{world_line}"
            f"【角色现有信息】\n{fields_str}\n\n"
            f"请补全这个角色的设定。保留已有字段，填充缺失的：\n"
            f"- name: 英文名（若已有则保留）\n"
            f"- display_name: 中文显示名\n"
            f"- color: #RRGGBB 格式\n"
            f"- description: 外貌+身份描述（30-60字）\n"
            f"- personality: 性格关键词（10-20字）\n"
            f"- system_prompt: 详细人设定义，包括语气、表达方式、口头禅\n"
            f"  对话用「」包裹，动作用*星号*描述\n\n"
            f"返回纯JSON对象，不要```代码块"
        )

    def complete_character_async(self, char_name: str, on_result, on_error=None):
        """异步补全角色。on_result(completed_char_dict) / on_error(msg)。"""
        from services.api_service import call_chat_completion_async
        if not config.API_KEY:
            if on_error:
                on_error("未配置 API Key")
            return

        prompt = self.build_complete_character_prompt(char_name)

        def _on_text(content):
            try:
                data, err = extract_json(content)
                if not data:
                    if on_error:
                        on_error(f"解析失败: {err}")
                    return
                if not isinstance(data, dict):
                    if on_error:
                        on_error("返回数据不是角色对象")
                    return
                on_result(data)
            except Exception as ex:
                if on_error:
                    on_error(str(ex))

        call_chat_completion_async(
            messages=[
                {"role": "system", "content": "你是角色设计师，只返回JSON对象。"},
                {"role": "user", "content": prompt},
            ],
            on_result=_on_text,
            on_error=on_error,
            temperature=0.85,
            max_tokens=1200,
            timeout=45.0,
        )

    def build_infer_world_prompt(self) -> str:
        """构建「推断世界观」prompt：从标题和场景推断世界观。"""
        title = self.app.title
        scene_lines = [f"- {s.get('time','')}·{s.get('location','')}: {s.get('scene','')[:60]}"
                       for s in (self.app.scenes or [])]
        scene_list = "\n".join(scene_lines) if scene_lines else "(无场景)"
        char_lines = [f"- {c.get('display_name', n)}: {c.get('description','')[:40]}"
                      for n, c in self.app.characters.items()]
        char_list = "\n".join(char_lines) if char_lines else "(无角色)"

        return (
            f"【剧本标题】\n{title}\n\n"
            f"【已有场景】\n{scene_list}\n\n"
            f"【已有角色】\n{char_list}\n\n"
            f"请根据以上信息，推断并生成这个剧本的世界观设定。\n"
            f"世界观应该是一个 1-3 句的描述，概括故事发生的背景、时代、地点等。\n\n"
            f"返回纯JSON：{{\"world\":\"世界观描述\"}}"
        )

    def infer_world_async(self, on_result, on_error=None):
        """异步推断世界观。on_result(world_str) / on_error(msg)。"""
        from services.api_service import call_chat_completion_async
        if not config.API_KEY:
            if on_error:
                on_error("未配置 API Key")
            return

        prompt = self.build_infer_world_prompt()

        def _on_text(content):
            try:
                data, err = extract_json(content)
                if not data:
                    if on_error:
                        on_error(f"解析失败: {err}")
                    return
                world = data.get("world", "")
                if not world:
                    if on_error:
                        on_error("返回数据缺少世界观")
                    return
                on_result(world)
            except Exception as ex:
                if on_error:
                    on_error(str(ex))

        call_chat_completion_async(
            messages=[
                {"role": "system", "content": "你是世界观设定师，只返回JSON。"},
                {"role": "user", "content": prompt},
            ],
            on_result=_on_text,
            on_error=on_error,
            temperature=0.8,
            max_tokens=300,
            timeout=30.0,
        )
