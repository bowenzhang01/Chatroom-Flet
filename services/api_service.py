# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · API 服务层
  封装所有 LLM HTTP 请求：chat completion / model list fetch
  支持同步和异步（后台线程）两种调用方式。
  零 UI 框架依赖：异步回调由调用方决定如何切回主线程
  （Flet 中 page.update() 跨线程安全，无需 Kivy Clock）。
"""

import threading
from typing import Callable, Optional

import httpx

import config
from utils import extract_json


# ── 通用错误类 ──

class APIError(Exception):
    """API 调用错误，携带人类可读消息"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _parse_error(e: Exception) -> str:
    """解析 HTTP/网络异常，返回人类可读消息"""
    msg = str(e)
    print(f"[api] 异常类型={type(e).__name__} 消息={msg}")
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 401:
            return "API Key 无效，请检查设置"
        elif code == 403:
            return "API 访问被拒绝，请检查 Key 权限"
        elif code == 429:
            return "API 请求太频繁，请稍后重试"
        elif code >= 500:
            return f"API 服务器错误 (HTTP {code})"
        else:
            return f"API 请求失败 (HTTP {code})"
    if "timed out" in msg.lower() or "timeout" in msg.lower():
        return "连接 API 超时，请检查网络"
    if "connection" in msg.lower() or "refused" in msg.lower():
        return "无法连接 API 服务器，请检查网络和地址"
    if "name resolution" in msg.lower() or "getaddrinfo" in msg.lower():
        return "无法解析 API 服务器地址（请确认 API 地址正确；WSL 环境请检查 /etc/resolv.conf DNS 配置）"
    return msg[:120]


# ── 核心 API 函数 ──

def call_chat_completion(
    messages: list,
    model: str = None,
    api_key: str = None,
    api_base: str = None,
    temperature: float = None,
    max_tokens: int = None,
    timeout: float = 30.0,
) -> str:
    """同步调用 LLM chat completion，返回响应文本。

    Args:
        messages: [{"role":"system","content":...}, {"role":"user","content":...}]
        model: 模型名，默认用 config.MODEL
        api_key: API Key，默认用 config.API_KEY
        api_base: API 地址，默认用 config.API_BASE
        temperature: 温度参数
        max_tokens: 最大 token 数
        timeout: 超时秒数

    Returns:
        LLM 返回的纯文本

    Raises:
        APIError: HTTP 或网络错误
    """
    if model is None:
        model = config.MODEL
    if api_key is None:
        api_key = config.API_KEY
    if api_base is None:
        api_base = config.API_BASE
    api_base = api_base.strip()
    if temperature is None:
        temperature = config.TEMPERATURE
    if max_tokens is None:
        max_tokens = config.MAX_TOKENS

    if not api_key:
        raise APIError("未配置 API Key")

    url = f"{api_base}/chat/completions"
    print(f"[api] POST {url} | model={model} | timeout={timeout}s")
    try:
        with httpx.Client(timeout=timeout, verify=False, trust_env=False) as client:
            r = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content
    except httpx.HTTPStatusError as e:
        raise APIError(_parse_error(e), e.response.status_code)
    except Exception as e:
        raise APIError(_parse_error(e))


def call_chat_completion_async(
    messages: list,
    on_result: Callable[[str], None],
    on_error: Callable[[str], None] = None,
    model: str = None,
    api_key: str = None,
    api_base: str = None,
    temperature: float = 0.7,
    max_tokens: int = 800,
    timeout: float = 30.0,
):
    """后台线程异步调用 LLM，通过回调返回结果。

    与 Kivy 版的区别：
    - 不再依赖 kivy.clock.Clock.schedule_once 切回主线程
    - 直接在后台线程调用回调；Flet 的 page.update() 是跨线程安全的
    - 若调用方需要确保主线程执行，可在回调内部自行调度

    Args:
        messages: 同 call_chat_completion
        on_result: 成功回调 on_result(response_text)
        on_error: 失败回调 on_error(error_message)
        其他参数: 同 call_chat_completion
    """
    if api_key is None:
        api_key = config.API_KEY
    if api_base is None:
        api_base = config.API_BASE

    def _run():
        try:
            result = call_chat_completion(
                messages=messages,
                model=model,
                api_key=api_key,
                api_base=api_base,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            if on_result:
                on_result(result)
        except APIError as e:
            if on_error:
                on_error(str(e))
        except Exception as e:
            if on_error:
                on_error(_parse_error(e))

    threading.Thread(target=_run, daemon=True).start()


def fetch_models(
    api_key: str = None,
    api_base: str = None,
    timeout: float = 15.0,
) -> list:
    """获取可用模型列表（同步）。

    Returns:
        模型 ID 列表（如 ["deepseek-chat", "deepseek-reasoner"]）

    Raises:
        APIError: 请求失败
    """
    if api_key is None:
        api_key = config.API_KEY
    if api_base is None:
        api_base = config.API_BASE
    api_base = api_base.strip()

    try:
        with httpx.Client(timeout=timeout, verify=False, trust_env=False) as client:
            r = client.get(
                f"{api_base}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            r.raise_for_status()
            return [m.get("id", "") for m in r.json().get("data", [])]
    except httpx.HTTPStatusError as e:
        raise APIError(_parse_error(e), e.response.status_code)
    except Exception as e:
        raise APIError(_parse_error(e))


def fetch_models_async(
    on_result: Callable[[list], None],
    on_error: Callable[[str], None] = None,
    api_key: str = None,
    api_base: str = None,
    timeout: float = 15.0,
):
    """后台线程获取模型列表，通过回调返回。"""
    def _run():
        try:
            models = fetch_models(api_key=api_key, api_base=api_base, timeout=timeout)
            if on_result:
                on_result(models)
        except APIError as e:
            if on_error:
                on_error(str(e))
        except Exception as e:
            if on_error:
                on_error(_parse_error(e))

    threading.Thread(target=_run, daemon=True).start()


def test_connection_async(
    on_result: Callable[[bool, str], None],
    api_key: str = None,
    api_base: str = None,
    timeout: float = 15.0,
):
    """测试 API 连接（后台线程）。
    回调签名 on_result(success: bool, message: str)。"""
    def _run():
        nonlocal api_key, api_base
        try:
            if api_key is None:
                api_key = config.API_KEY
            if api_base is None:
                api_base = config.API_BASE
            api_base = api_base.strip() if api_base else api_base
            with httpx.Client(timeout=timeout, verify=False, trust_env=False) as client:
                r = client.get(
                    f"{api_base}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                r.raise_for_status()
                data = r.json()
                count = len(data.get("data", []))
                on_result(True, f"连接正常，可用模型 {count} 个")
        except APIError as e:
            on_result(False, str(e))
        except Exception as e:
            on_result(False, _parse_error(e))

    threading.Thread(target=_run, daemon=True).start()
