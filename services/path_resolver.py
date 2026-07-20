# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 平台路径抽象
  统一处理开发模式 / 打包后(Windows/macOS/Linux/Android/iOS/Web)的 writable
  目录与 bundled 资源复制。
  不再依赖 Kivy 的 jnius/PythonActivity；改用平台标准数据目录。
"""

import os
import shutil
import sys
from pathlib import Path

import config
from utils import load_json


def is_packaged() -> bool:
    """当前运行在打包后的可执行文件/APK/iOS 中（非开发模式）。

    PyInstaller 打包: sys.frozen == True, 资源在 sys._MEIPASS
    serious-python(Android/iOS): sys.platform in ("android","ios")
    """
    return getattr(sys, "frozen", False) or sys.platform in ("android", "ios")


def get_data_dir() -> Path:
    """返回 OS 标准应用数据目录。

    • Windows:   %APPDATA%/dorm-flet
    • macOS:     ~/Library/Application Support/dorm-flet
    • Linux:     $XDG_DATA_HOME/dorm-flet 或 ~/.local/share/dorm-flet
    • Android:   ~(沙盒 files_dir 即 /data/data/.../files)
    • iOS:       同上,沙盒内 Path.home()
    """
    plat = sys.platform
    if plat == "win32":
        base = Path(os.environ.get("APPDATA", "") or os.path.expandvars("%USERPROFILE%\\AppData\\Roaming"))
    elif plat == "darwin":
        try:
            base = Path.home() / "Library" / "Application Support"
        except (RuntimeError, OSError):
            # macOS 沙盒或异常环境：home() 可能失败，回退到环境变量
            base = Path(os.environ.get("HOME", ".")) / "Library" / "Application Support"
    elif plat in ("android", "ios"):
        # Android/iOS：serious-python 设置 $HOME 为沙盒 files_dir；Path.home() 可能失败
        home_env = os.environ.get("HOME", "")
        if home_env:
            base = Path(home_env)
        else:
            # 兜底：尝试 expanduser，失败则用当前目录（最后手段）
            try:
                base = Path(os.path.expanduser("~"))
            except (RuntimeError, OSError):
                base = Path(".")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", "") or Path.home() / ".local" / "share")
    return base / "dorm-flet"


def setup_workspace() -> Path:
    """应用启动时调用。确定 writable 目录，必要时复制 bundled 数据。

    开发模式(is_packaged() == False): 直接用项目目录
    打包后: 首次启动将 bundled profiles + config 复制到数据目录,之后原地读写
    """
    if not is_packaged():
        # 开发模式：config.py 读取 bundle config.json 后，若不存在则从 example 复制
        _ensure_dev_config()
        config.PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        return config.PROFILES_DIR

    data_dir = get_data_dir()
    writable_profiles = data_dir / "profiles"
    writable_config = data_dir / "config.json"
    data_dir.mkdir(parents=True, exist_ok=True)

    bundled_config = config.BASE_DIR / "config.json"
    bundled_example = config.BASE_DIR / "config.example.json"

    # 复制 bundled profiles 到可写目录（仅首次）
    if config.PROFILES_DIR.exists() and not writable_profiles.exists():
        # 复制到临时目录后 rename，保证原子性（避免中断后砖化）
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="dorm_copy_", dir=str(data_dir)))
        try:
            shutil.copytree(str(config.PROFILES_DIR), str(tmp / "profiles"))
            (tmp / "profiles").rename(writable_profiles)
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)
            raise

    # 复制 config.json（首次）：优先用 bundled config，否则用 example
    if not writable_config.exists():
        src = bundled_config if bundled_config.exists() else bundled_example
        if src.exists():
            shutil.copy(str(src), str(writable_config))

    config.BASE_DIR = data_dir
    config.PROFILES_DIR = writable_profiles
    # 重新加载 app_config（开发模式下 config.py 已读 bundle 内的，此处覆盖为数据目录的）
    config.app_config = load_json(writable_config, default={})
    # 同步所有从 app_config 派生的模块级常量（API_KEY/API_BASE/MODEL/ACTIVE_PROFILE/SSL 等）
    _sync_config_from_app_config()
    return config.PROFILES_DIR


def _ensure_dev_config():
    """开发模式下，若 bundle config.json 不存在则从 example 复制并重新加载。"""
    cfg = config.BASE_DIR / "config.json"
    if not cfg.exists():
        example = config.BASE_DIR / "config.example.json"
        if example.exists():
            shutil.copy2(str(example), str(cfg))
            # 重新加载 app_config（config.py import 时读到了空 dict）
            config.app_config = load_json(cfg, default={})
            _sync_config_from_app_config()


def _sync_config_from_app_config():
    """从 config.app_config 同步模块级常量（setup_workspace 替换 app_config 后调用）。"""
    mc = config.app_config.get("model", {})
    if mc.get("api_base"):
        config.API_BASE = mc["api_base"]
    if mc.get("model"):
        config.MODEL = mc["model"]
    if mc.get("models"):
        config.MODELS_LIST = mc["models"]
    if mc.get("temperature") is not None:
        config.TEMPERATURE = mc["temperature"]
    if mc.get("max_tokens") is not None:
        config.MAX_TOKENS = mc["max_tokens"]
    # API_KEY：优先环境变量，其次配置文件；resolve_key 内部已处理优先级
    config.API_KEY = config.resolve_key()
    # ACTIVE_PROFILE：config.py import 时从空/旧 app_config 读的可能是错的
    config.ACTIVE_PROFILE = config.app_config.get("active_profile", config.ACTIVE_PROFILE)
    behavior = config.app_config.get("behavior", {})
    if "streaming" in behavior:
        config.STREAMING_ENABLED = behavior["streaming"]
    network = config.app_config.get("network", {})
    if "verify_ssl" in network:
        config.API_VERIFY_SSL = network["verify_ssl"]
    if "trust_env" in network:
        config.API_TRUST_ENV = network["trust_env"]
