# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 平台路径抽象
  统一处理桌面端 / Android / iOS / Web 的可写目录与 bundled 资源复制。
  Flet 版用此模块替代 Kivy 版 main.py 中的 _setup_workspace()。

  桌面/Web: 直接用项目目录（config.BASE_DIR / config.PROFILES_DIR）
  Android/iOS: 首次启动将 bundled profiles/ 复制到 user_data_dir，
              之后从可写目录读写。
"""

import shutil
import sys
from pathlib import Path

import config
from utils import load_json, save_json


def is_mobile() -> bool:
    """是否运行在 Android/iOS 原生环境"""
    return getattr(sys, "platform", "") in ("android", "ios")


def get_user_data_dir() -> Path:
    """获取应用可写目录。
    Android/iOS: 通过 pyjnius 获取 context files dir（Flet 内部已封装）；
    桌面/Web: 返回 config.BASE_DIR。"""
    if is_mobile():
        try:
            # Flet 在 Android 通过 flet 的 platform API 暴露路径
            # 优先用 jnius 获取 Context.getFilesDir()
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            ctx = PythonActivity.mActivity
            files_dir = ctx.getFilesDir().getAbsolutePath()
            return Path(files_dir)
        except Exception:
            try:
                # 备选：flet 包内部路径
                import flet
                return Path(flet.__file__).parent / "data"
            except Exception:
                pass
    return config.BASE_DIR


def setup_workspace() -> Path:
    """应用启动时调用。确定可写工作目录，必要时复制 bundled 数据。
    返回最终的 profiles 目录路径。"""
    if not is_mobile():
        # 桌面/Web：直接用项目目录，无需复制
        config.PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        return config.PROFILES_DIR

    # ── 移动端：复制 bundled 数据到可写目录 ──
    ud = get_user_data_dir()
    bundled_profiles = config.PROFILES_DIR
    writable_profiles = ud / "profiles"
    bundled_config = config.BASE_DIR / "config.json"
    writable_config = ud / "config.json"

    if bundled_profiles.exists() and not writable_profiles.exists():
        shutil.copytree(str(bundled_profiles), str(writable_profiles))

    if bundled_config.exists() and not writable_config.exists():
        shutil.copy(str(bundled_config), str(writable_config))

    # 切换全局路径到可写目录
    config.BASE_DIR = ud
    config.PROFILES_DIR = writable_profiles
    config.app_config = load_json(writable_config)
    return config.PROFILES_DIR
