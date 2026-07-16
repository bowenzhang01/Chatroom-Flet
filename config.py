# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 全局配置与路径常量
  所有模块通过 `import config` 访问配置，使用 `config.API_KEY = xxx` 修改。
  本文件零 UI 框架依赖（Flet 字体注册在 app/theme.py 完成）。
"""

import os
from pathlib import Path

from utils import load_json

# ═══ 路径常量 ═══
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
PROFILES_DIR = BASE_DIR / "profiles"
ASSETS_DIR = BASE_DIR / "assets"

# ═══ 字体文件路径（供 Flet page.fonts 注册，不再用 Kivy LabelBase）═══
FONT_SC_PATH = ASSETS_DIR / "NotoSansSC-Regular.ttf"
FONT_SC_NAME = "Noto Sans SC"  # Flet 内部引用名

# ═══ 全局 JSON 配置（跨剧本共享的 API / App 设置）═══
app_config = load_json(BASE_DIR / "config.json")


def resolve_key():
    """按优先级解析 API Key：环境变量 > config.json
    环境变量：DEEPSEEK_API_KEY 或 OPENAI_API_KEY"""
    k = os.environ.get("DEEPSEEK_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    if k:
        return k
    k = app_config.get("model", {}).get("api_key", "")
    if k:
        return k
    return ""


def key_source() -> str:
    """返回 API Key 来源：'env' | 'file' | ''（未配置）"""
    if os.environ.get("DEEPSEEK_API_KEY", "") or os.environ.get("OPENAI_API_KEY", ""):
        return "env"
    if app_config.get("model", {}).get("api_key", ""):
        return "file"
    return ""


# ═══ 模块级导出（跨文件访问，修改时直接赋值 config.XXX = ...）═══
API_KEY = resolve_key()
MC = app_config.get("model", {})
API_BASE = MC.get("api_base", "https://api.deepseek.com")
MODEL = MC.get("model", "deepseek-chat")
MODELS_LIST = MC.get("models", [])
TEMPERATURE = MC.get("temperature", 0.85)
MAX_TOKENS = MC.get("max_tokens", 300)
ACTIVE_PROFILE = app_config.get("active_profile", "dorm_life")

# ═══ 随机事件默认参数（用户不可调，仅作为内置常量）═══
RANDOM_EVENT_DEFAULTS = {
    "min_cooldown": 3,
    "ramp_length": 10,
    "max_probability": 0.35,
    "event_weight": 0.5,
}
