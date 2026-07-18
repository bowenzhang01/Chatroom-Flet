# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 全局配置与路径常量
  所有模块通过 `import config` 访问配置，使用 `config.API_KEY = xxx` 修改。
  本文件零 UI 框架依赖（Flet 字体注册在 app/theme.py 完成）。
"""

import os
import shutil
import sys as _sys
from pathlib import Path

from utils import load_json

# ═══ 路径常量 ═══
# 打包后(PyInstaller/serious-python)__file__不可靠,
# 用 sys._MEIPASS 定位 bundled 资源
if getattr(_sys, 'frozen', False):
    _bundle_dir = Path(_sys._MEIPASS)
else:
    _bundle_dir = Path(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = _bundle_dir
PROFILES_DIR = _bundle_dir / "profiles"
ASSETS_DIR = _bundle_dir / "assets"

# ═══ 字体文件路径（供 Flet page.fonts 注册，不再用 Kivy LabelBase）═══
FONT_SC_PATH = ASSETS_DIR / "NotoSansSC-Regular.ttf"
FONT_SC_NAME = "Noto Sans SC"  # Flet 内部引用名

# ═══ 全局 JSON 配置（跨剧本共享的 API / App 设置）═══
_config_path = BASE_DIR / "config.json"
if not _config_path.exists():
    _example_path = BASE_DIR / "config.example.json"
    if _example_path.exists():
        shutil.copy2(_example_path, _config_path)
app_config = load_json(_config_path, default={})


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

# ═══ SSL / 代理配置 ═══
API_VERIFY_SSL = True   # HTTPS 证书校验；自签证书环境需关闭
API_TRUST_ENV = True    # 读取系统代理环境变量；WSL 代理冲突时可关闭

# ═══ 随机事件默认参数（用户不可调，仅作为内置常量）═══
RANDOM_EVENT_DEFAULTS = {
    "min_cooldown": 3,
    "ramp_length": 10,
    "max_probability": 0.35,
    "event_weight": 0.5,
}

# ═══ UI 行为配置 ═══
BEHAVIOR = app_config.get("behavior", {})
STREAMING_ENABLED = BEHAVIOR.get("streaming", True)  # 流式输出，默认开启
