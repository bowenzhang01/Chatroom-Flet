# -*- coding: utf-8 -*-
"""ChatRoom - Flet Edition · 可复用进度对话框

  统一风格：AlertDialog + ProgressBar + 状态文本 + 步骤列表。
  用于 AI 生成（剧本/场景/角色/补全/推断）和对话保存。

  ProgressBar 策略：
  - 单次 API 调用（无法细粒度跟踪）→ 不确定模式（value=None，自动动画）
  - 多步操作 → 确定模式（value=0..1），每步更新
   - 完成时 → value=1.0 + ✓ 图标，显示关闭按钮供用户手动关闭
"""

import asyncio

import flet as ft

from app.theme import TEXT_ML, TEXT_SM
__all__ = ["ProgressDialog"]


class ProgressDialog:
    """可复用的进度对话框。

    用法::

        dlg = ProgressDialog(page, title="✨ AI 生成中")
        dlg.show(status="正在生成场景…", steps=["解析描述", "生成场景", "写入剧本"])

        # 异步更新：
        dlg.set_step(1, "正在生成场景…")
        dlg.complete("已生成 5 个场景", on_close=lambda: refresh_ui())

        # 出错：
        dlg.fail("生成失败：网络超时")

    也可用于不确定进度的单步操作::

        dlg = ProgressDialog(page, title="💾 保存对话")
        dlg.show(status="正在生成标题…", indeterminate=True)
    """

    def __init__(self, page: ft.Page, title: str = "处理中"):
        self.page = page
        self._title = title
        self._dialog: ft.AlertDialog = None
        self._status: ft.Text = None
        self._progress: ft.ProgressBar = None
        self._steps_col: ft.Column = None
        self._step_controls: list = []
        self._close_btn: ft.TextButton = None
        self._on_close_cb = None
        self._closed = False
        self._async_loop = None
        try:
            self._async_loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

    def show(self, status: str = "正在处理…", steps: list = None,
             indeterminate: bool = True, dismissible: bool = False):
        """显示进度对话框。

        Args:
            status: 初始状态文本
            steps: 步骤列表（每项是步骤名称字符串）；None 则不显示步骤
            indeterminate: True=不确定进度条（动画）; False=确定进度条（需手动 set_progress）
            dismissible: True=允许点击遮罩关闭
        """
        self._status = ft.Text(status, size=TEXT_SM, weight=ft.FontWeight.W_500)
        self._progress = ft.ProgressBar(
            value=None if indeterminate else 0.0,
            width=320,
        )
        self._steps_col = ft.Column(spacing=6)
        self._step_controls = []
        if steps:
            for i, label in enumerate(steps):
                row = ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.RADIO_BUTTON_UNCHECKED, size=18,
                                color=ft.Colors.OUTLINE),
                        ft.Text(label, size=TEXT_SM),
                    ],
                    spacing=8,
                )
                self._step_controls.append(row)
                self._steps_col.controls.append(row)

        self._close_btn = ft.TextButton("关闭", on_click=lambda e: self.close(),
                                        visible=False)

        content_controls = [self._status, self._progress]
        if self._step_controls:
            content_controls.append(ft.Container(height=4))
            content_controls.append(self._steps_col)
        content_controls.append(self._close_btn)

        self._dialog = ft.AlertDialog(
            title=ft.Text(self._title, size=TEXT_ML, weight=ft.FontWeight.W_700),
            content=ft.Column(controls=content_controls, tight=True, spacing=10),
            actions=[],
            modal=not dismissible,
        )
        self.page.show_dialog(self._dialog)

    def set_status(self, text: str):
        """更新状态文本。"""
        if self._status and not self._closed:
            self._status.value = text
            self._safe_update()

    def set_progress(self, value: float):
        """设置确定进度条值 (0.0 ~ 1.0)。"""
        if self._progress and not self._closed:
            self._progress.value = max(0.0, min(1.0, value))
            self._safe_update()

    def set_progress_fraction(self, done: int, total: int, status: str = None):
        """以分数形式显示进度：更新状态文本 + 确定进度条。

        Args:
            done: 已完成数
            total: 总数
            status: 状态文本前缀（如"正在生成"），自动追加 (done/total)
        """
        if self._closed:
            return
        if self._progress:
            self._progress.value = None if total == 0 else done / total
        if status:
            self.set_status(f"{status} ({done}/{total})")
        else:
            self._safe_update()

    def set_step(self, step_idx: int, status: str = None, delay: float = 0.0):
        """标记某个步骤为已完成（打勾），并可选更新状态文本。

        Args:
            step_idx: 步骤索引（0-based）；当前步骤会显示为进行中
            status: 可选的新状态文本
            delay: 可选延迟（秒），用于让步骤过渡可见；仅在非主线程调用时有意义
        """
        if self._closed:
            return
        if delay > 0:
            import time as _time
            _time.sleep(delay)
        for i, row in enumerate(self._step_controls):
            icon = row.controls[0]
            if i < step_idx:
                icon.icon = ft.Icons.CHECK_CIRCLE
                icon.color = ft.Colors.TERTIARY
            elif i == step_idx:
                icon.icon = ft.Icons.PENDING
                icon.color = ft.Colors.PRIMARY
            else:
                icon.icon = ft.Icons.RADIO_BUTTON_UNCHECKED
                icon.color = ft.Colors.OUTLINE
        if status:
            self.set_status(status)
        else:
            self._safe_update()

    def complete(self, summary: str, on_close=None, auto_close_ms: int = 0):
        """标记完成：进度条满 + 全部打勾 + 显示关闭按钮。

        Args:
            summary: 完成提示文本
            on_close: 关闭时的回调
            auto_close_ms: 自动关闭延迟（毫秒）；0=不自动关闭
        """
        if self._closed:
            if on_close:
                on_close()
            return
        if self._progress:
            self._progress.value = 1.0
        for row in self._step_controls:
            icon = row.controls[0]
            icon.icon = ft.Icons.CHECK_CIRCLE
            icon.color = ft.Colors.TERTIARY
        if self._status:
            self._status.value = summary
            self._status.color = ft.Colors.TERTIARY
        if self._close_btn:
            self._close_btn.visible = True
        self._on_close_cb = on_close
        self._safe_update()
        if auto_close_ms > 0:
            import threading
            def _auto():
                import time as _t
                _t.sleep(auto_close_ms / 1000.0)
                self.close()
            threading.Thread(target=_auto, daemon=True).start()

    def fail(self, error_msg: str, on_close=None):
        """标记失败：显示错误 + 关闭按钮。"""
        if self._closed:
            if on_close:
                on_close()
            return
        if self._progress:
            self._progress.value = 0.0
            self._progress.color = ft.Colors.ERROR
        if self._status:
            self._status.value = error_msg
            self._status.color = ft.Colors.ERROR
        if self._close_btn:
            self._close_btn.visible = True
        self._on_close_cb = on_close
        self._safe_update()

    def close(self):
        """关闭对话框并触发 on_close 回调。"""
        if self._closed:
            return
        self._closed = True
        try:
            if self._dialog is not None:
                self._dialog.open = False
                self.page.update()
        except Exception:
            try:
                self.page.pop_dialog()
            except Exception:
                pass
        if self._on_close_cb:
            try:
                self._on_close_cb()
            except Exception:
                pass

    def _safe_update(self):
        try:
            if self._async_loop and self._async_loop.is_running():
                self._async_loop.call_soon_threadsafe(self.page.update)
            else:
                self.page.update()
        except Exception:
            pass
