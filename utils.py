# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 纯工具函数（无状态、零 UI 框架依赖）
  load_json / save_json / hex_to_rgba / extract_json
  注：Kivy 版的 make_popup_label 已删除，UI 层用 Flet 控件自行构建。
"""

import json
import re as _re
from pathlib import Path


def load_json(path):
    """接受 Path 对象或字符串，返回解析后的 JSON。
    配置文件缺失返回 {}，其他缺失返回 []。"""
    p = Path(path) if not isinstance(path, Path) else path
    if not p.exists():
        return {} if "config" in str(p) else []
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[load_json] 读取失败 {p}: {e}")
        return {} if "config" in str(p) else []


def save_json(path, data):
    """安全写入 JSON（自动创建父目录）"""
    p = Path(path) if not isinstance(path, Path) else path
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[save_json] 保存失败 {p}: {e}")
        return False


def hex_to_rgba(h, a=1.0):
    """hex 颜色字符串 → (r, g, b, a) 浮点元组。
    保留给可能需要 RGBA 元组的旧逻辑使用；Flet UI 层建议直接用 hex 字符串。"""
    h = h.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
        return (r, g, b, a)
    return (1, 1, 1, a)


def extract_json(text: str):
    """从 AI 返回文本中提取 JSON，处理 markdown 代码块和常见格式错误。

    支持 dict 和 list 两种根类型。
    返回 (dict|list|None, error_msg|None)
    """
    if not text or not text.strip():
        return None, "AI返回为空"
    # Step 0: 移除 DeepSeek R1 等模型的 <think>...</think> 思考标签
    text = _re.sub(r'<think>[\s\S]*?</think>', '', text)
    text = text.strip()
    if not text:
        return None, "AI返回为空（仅含思考标签）"

    # Step 1: 提取 markdown 代码块
    m = _re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, _re.DOTALL)
    if m:
        text = m.group(1).strip()

    # Step 2: 尝试直接解析（最理想情况：纯 JSON）
    result = _try_parse_json(text)
    if result is not None:
        return result, None

    # Step 3: 找最外层结构
    # 判断根类型：看第一个非空白字符是 { 还是 [
    stripped = text.lstrip()
    if stripped.startswith('['):
        # 数组：找最外层 [ ... ]（贪心匹配到最后一个 ]）
        m = _re.search(r'\[[\s\S]*\]', text)
        if m:
            candidate = m.group(0)
            result = _try_parse_json(candidate)
            if result is not None:
                return result, None
    elif stripped.startswith('{'):
        # 对象：找最外层 { ... }
        m = _re.search(r'\{[\s\S]*\}', text)
        if m:
            candidate = m.group(0)
            result = _try_parse_json(candidate)
            if result is not None:
                return result, None
    else:
        # 不以 { 或 [ 开头：找最先出现的结构类型
        brace_pos = text.find('{')
        bracket_pos = text.find('[')
        # 选择最先出现的（-1 表示不存在）
        if bracket_pos >= 0 and (brace_pos < 0 or bracket_pos < brace_pos):
            # 数组在前面或只有数组
            m = _re.search(r'\[[\s\S]*\]', text)
            if m:
                candidate = m.group(0)
                result = _try_parse_json(candidate)
                if result is not None:
                    return result, None
        if brace_pos >= 0:
            m = _re.search(r'\{[\s\S]*\}', text)
            if m:
                candidate = m.group(0)
                result = _try_parse_json(candidate)
                if result is not None:
                    return result, None
        # 兜底：尝试另一种
        m = _re.search(r'\[[\s\S]*\]', text)
        if m:
            candidate = m.group(0)
            result = _try_parse_json(candidate)
            if result is not None:
                return result, None

    return None, "JSON解析失败"


def _try_parse_json(text: str):
    """尝试解析 JSON 文本，自动修复常见错误。
    返回 dict/list 或 None（解析失败）。"""
    # 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 修复尾部多余逗号
    try:
        fixed = _re.sub(r',\s*([}\]])', r'\1', text)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    # 修复单引号 → 双引号
    try:
        fixed = _re.sub(r"'([^']*)'", r'"\1"', text)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    # 尝试 json5 宽松解析（如果可用）
    try:
        import json5
        return json5.loads(text)
    except Exception:
        pass
    return None
