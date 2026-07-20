# ChatRoom · Flet Edition 第三轮代码审查错误报告

| 项 | 值 |
|---|---|
| 审查日期 | 2026-07-20 |
| 审查范围 | 流式输出 + 回到底部按钮改动后的全平台回归审查（33 个 Python 源文件） |
| 审查方法 | 静态通读 + 用户视角操作流程推演 + 线程时序分析 + 跨平台差异分析 + 修复回归分析 |
| 问题总数 | 47 条 Bug（P0×2, P1×12, P2×18, P3×15） |
| 已修复 | 阶段 1 完成 18 条（含 10 条原计划 + 8 条回归修复） |
| 待修复 | 阶段 2-3 共 29 条 |

---

## 修复状态

| 编号 | 严重度 | 状态 | 修复日期 |
|---|---|---|---|
| P0-1, P0-2 | P0 | ✅ 已修复 | 2026-07-20 |
| P1-1, P1-2, P1-5, P1-6, P1-7 | P1 | ✅ 已修复 | 2026-07-20 |
| P2-W3, P2-N1, P2-N2 | P2 | ✅ 已修复 | 2026-07-20 |
| A3 (高频 update 节流) | P2 | ✅ 已修复 | 2026-07-20 |
| REG-1 ~ REG-8 | 回归 | ✅ 已修复 | 2026-07-20 |
| P1-8 ~ P1-12 | P1 | ⏳ 阶段 2 待修复 | — |
| P2 其余 15 条 | P2 | ⏳ 阶段 2-3 待修复 | — |
| P3 共 15 条 | P3 | ⏳ 阶段 3 待修复 | — |

---

## 审查背景

本轮审查针对用户反馈"流式输出与回到底部按钮改动后，macOS Web 出现 bug 而 Windows Web 正常"的问题，重点检查：

1. 流式管线（msg → msg_delta → msg_end）在不同平台的线程安全与事件顺序
2. 回到底部按钮动态插入/移除逻辑的状态一致性
3. 跨平台差异（Windows / macOS / Android / iOS / Windows Web / macOS Web）
4. 前两轮 BUG_REPORT.md / BUG_REPORT_2.md 修复的回归

### macOS Web vs Windows Web 差异根因

用户朋友报告"被困在顶部"，用户描述"被困在底部"——两者实为同一根因的两面：

| 编号 | 根因 | macOS Web vs Windows Web |
|---|---|---|
| A1 (P2-W3) | `_on_msg_delta` 强制 `auto_scroll` 覆盖用户滚动 | Safari WebSocket 延迟高于 Chrome，`_near_bottom` 更新滞后 → 上滚被拉回底部（"困在底部"） |
| A4 (P1-1) | `_streaming_count` 卡死 → 回到底部按钮永久失效 | Web 端 WS 断连/重连更易导致 `msg_end` 丢失 → 按钮永不出现（"困在顶部"） |
| A2 (P1-7) | `trust_env=True` 在 macOS 系统代理下破坏 SSE | macOS 企业代理缓冲 SSE / 注入 SSL MITM；Windows 通常不配系统代理 |
| A3 | 高频 `page.update()` 淹没 WebSocket | Safari WebSocket 对高频小消息处理效率低于 Chrome → 渲染卡顿 |

---

## 阶段 1 已修复的 Bug

### P0-1 / P0-2 · stop() 无法中断流式 HTTP + 孤儿线程复活 ✅

**定位**：`core/dialogue_loop.py:147-182`（stop）、`core/dialogue_loop.py:106-109`（start）、`services/api_service.py:177-260`（SSE 流式）

**原问题**：
- `stop()` 调 `join(timeout=5.0)` 但 loop 线程阻塞在 `httpx.Response.iter_lines()`，5s 超时后孤儿线程仍存活
- `start()` 的 `_stop_event.clear()` 是共享 Event，孤儿线程 `iter_lines()` 返回后不 break → 双 loop 线程并发
- 表现：停止后重新开始，消息变成两份；turn_count 跳变

**修复**：
1. `call_chat_completion_stream` 新增 `stop_check` 参数，每个 SSE 行 + 每个 token 前检查；中断时抛 `StreamInterrupted`，catch 后返回累积文本
2. `AIEngine._stop_check()` 返回 `self.app.loop._stop_event.is_set()`
3. `start()` 加孤儿线程检测：若 `_thread.is_alive()` 则 `_stop_event.set()` + 等 10s，超时则 abort start 并提示"上轮对话未完全停止，请稍后重试"

**残留限制**：`stop_check` 仅在 SSE 行间触发，若服务端长时间无数据，最长需等 read timeout（120s）才能退出。阶段 2 计划保存 httpx Client 句柄，stop 时 `client.close()` 强制中断。

---

### P1-1 (A4) · _streaming_count/_streaming_rows 状态泄漏 ✅

**定位**：`app/views/chat_view.py:53-54, 349-360, 817-833, 880-896`

**原问题**：
- 流式中导航离开 → `on_leave` 取消订阅 → `msg_end` 丢失 → `_streaming_count` 永远 >0
- `_on_scroll:248` 的 `if _streaming_count == 0` 永不成立 → 回到底部按钮永不出现
- 用户"被困在顶部"无法一键回到底部

**修复**：
1. 新增 `_reset_streaming_state()` 方法：清空 `_streaming_rows`、`_streaming_count=0`、`_user_scrolled=False`、取消 `_delta_update_timer`、强制 `_sync_bottom_btn(False)`
2. `_reset_to_empty` / `_reload_history_into_list` / `on_leave` 均调用此方法
3. `_on_streaming_start`：`msg_id` 为空时不递增 `_streaming_count`（避免计数只增不减）
4. `_on_msg_end`：`row is None` 时不递减计数（避免错减别人的计数）

---

### P1-2 · _stream_npc_dialogue 无 finally 保证 msg_end ✅

**定位**：`core/dialogue_loop.py:509-528`

**原问题**：NPC 流式路径无 `try/finally`，`post_process` 抛异常时 `msg_end` 永不触发 → NPC 气泡永远停留流式态 + `_streaming_count` 永不递减

**修复**：
1. `generate_fn` 用 try/except 包裹，异常不静默 pass 而是 print
2. `post_process` + `msg_end` 用 try/except 包裹，异常时仍 emit msg_end
3. `is_farewell` 的 `_active_npc` 清理移到 `finally` 块，确保所有路径都执行（修复回归分析发现的 BUG-2）

---

### P1-5 · Path.home() 在 Android/iOS 可能崩溃 ✅

**定位**：`services/path_resolver.py:36-44`

**原问题**：`Path.home()` 在 Android serious-python 环境可能抛 `RuntimeError` → 首次启动崩溃

**修复**：Android/iOS 优先用 `$HOME` 环境变量；`Path.home()` 和 `expanduser` 均加 try/except 兜底到当前目录

---

### P1-6 · config.py import 时写只读 bundle 目录 ✅

**定位**：`config.py:33-36` + `services/path_resolver.py:48-73`

**原问题**：`config.py` import 时 `shutil.copy2(config.example.json, config.json)` 写入 `BASE_DIR`，在 Android/iOS/某些 macOS 打包方式下 `BASE_DIR` 只读 → `PermissionError` → import 崩溃

**修复**：
1. `config.py` 移除 import-time 复制，只读 `app_config`（不存在则空载）
2. `setup_workspace` 开发模式调 `_ensure_dev_config`（复制 + 重新加载 + 同步常量）
3. 打包模式用临时目录 rename 保证原子性（修复 P2-6 copytree 中断砖化）
4. 新增 `_sync_config_from_app_config` 同步所有派生常量（含 API_KEY / ACTIVE_PROFILE / SSL / 代理等，修复回归分析发现的 BUG-1）

---

### P1-7 (A2) · trust_env=True 在 macOS 代理破坏 SSE + 设置页加 SSL/代理开关 ✅

**定位**：`config.py:72-73` + `app/views/settings_view.py` API 卡片 + `services/path_resolver.py:_sync_config_from_app_config`

**原问题**：
- `API_TRUST_ENV = True` 硬编码，httpx 在 macOS 上读取系统网络偏好设置中的代理
- 企业代理缓冲 SSE / 注入 SSL MITM → 流式卡顿/超时
- Windows 用户通常不配系统代理 → 不受影响（macOS Web vs Windows Web 差异根因之一）

**修复**：
1. `config.py` 的 `API_VERIFY_SSL` / `API_TRUST_ENV` 改为从 `app_config["network"]` 读取
2. 设置页 API 卡片新增"校验 SSL 证书"和"读取系统代理"两个 Switch + 提示文案
3. `_on_network_change` 立即更新 config + 持久化 + snack 反馈
4. `_sync_api_fields` 同步两个 switch 的值

---

### P2-W3 (A1) · _on_msg_delta 强制 auto_scroll 覆盖用户滚动 ✅

**定位**：`app/views/chat_view.py:623-641`（_on_msg_delta）+ `app/views/chat_view.py:242-251`（_on_scroll）

**原问题**：
- `_on_msg_delta` 用 `was_near = self._near_bottom` 判断是否强制 `auto_scroll=True`
- Web 端 `_on_scroll` 事件经 WebSocket 往返才能更新 `_near_bottom`
- Safari WebSocket 延迟高于 Chrome → 用户已上滚但 `_near_bottom` 仍为 True → 被拉回底部（"困在底部"）

**修复**：
1. 新增 `_user_scrolled` 标志：`_on_scroll` 中"非底部 + 非程序滚动"即置 True，回到底部时清除
2. `_on_msg_delta` / `_on_msg_end` 用 `_user_scrolled` 判断是否跟随，而非直接读 `_near_bottom`
3. 新增 `_program_scroll` 标志：`_scroll_to_bottom` 期间置 True，避免误判为用户上滚（0.4s Timer 后清除）
4. `auto_scroll` 仅在状态变化时设置，避免每帧重置导致近底部吸附（修复 P3-5）

---

### P2-N1 · SSE 要求 data: 含空格不兼容部分服务端 ✅

**定位**：`services/api_service.py:232`

**原问题**：`line.startswith("data: ")` 要求恰好一个空格，不兼容 `data:{...}`（vLLM/TGI 等自建服务端）

**修复**：改为 `line.startswith("data:")` 后 `[5:].lstrip()`，兼容无空格/多空格/tab

---

### P2-N2 · read timeout 60s 对推理模型不够 ✅

**定位**：`services/api_service.py:185, 212`

**原问题**：单一 timeout 60s 同时用于 connect/read/write，推理模型首 token 可能 60-120s → ReadTimeout

**修复**：float timeout 自动转为 `httpx.Timeout(connect=10, read=timeout*2, write=10, pool=10)`，read 给 120s

---

### A3 · 高频 page.update() 在 Safari WebSocket 上卡顿 ✅

**定位**：`app/views/chat_view.py:688-701, 639`

**原问题**：每条流式消息 ~23 次 `page.update()`，Safari WebSocket 对高频小消息处理效率低于 Chrome

**修复**：`_on_msg_delta` 新增 `_schedule_delta_update`，合并 100ms 内的多次 delta update 为一次 `page.update()`；`_on_msg_end` 的 `_finalize_msg_end` 取消挂起定时器并立即 push 最终内容

---

## 阶段 1 回归修复

### REG-1 · _sync_config_from_app_config 未同步 API_KEY ✅

**定位**：`services/path_resolver.py:122-142`

**原问题**：`_sync_config_from_app_config` 同步了 API_BASE/MODEL/TEMPERATURE 等，唯独漏掉 API_KEY。打包模式下用户外部编辑 config.json 添加 key 后重启，密钥不会被拾取 → 设置页显示"来源: 配置文件"却显示"未配置"

**修复**：加 `config.API_KEY = config.resolve_key()` + `config.ACTIVE_PROFILE = config.app_config.get("active_profile", config.ACTIVE_PROFILE)`

---

### REG-2 · _stream_npc_dialogue 异常路径跳过 farewell 清理 ✅

**定位**：`core/dialogue_loop.py:541-548`

**原问题**：post_process 抛异常时 `return response` 提前退出，跳过 `if is_farewell:` 的 `_active_npc` 清理 → NPC 状态机卡死，`_should_trigger_random` 持续返回 False 抑制随机事件

**修复**：`is_farewell` 清理移到 `finally` 块，确保所有路径都执行

---

### REG-3 · _user_scrolled 在程序滚动 0.4s 窗口内被误判 ✅

**定位**：`app/views/chat_view.py:252-253, 600-602`

**原问题**：原判定依赖 `_near_bottom` True→False 跳变，程序滚动窗口内跳变被消耗后，`_user_scrolled` 永久保持 False。Safari 端若 `_near_bottom` 报告过时的 True，强制滚动劫持用户上滚，修复失效。

**修复**：放宽判定为"非底部 + 非程序滚动即置位"，去掉跳变依赖

---

### REG-4 · on_leave 未取消 _delta_update_timer ✅

**定位**：`app/views/chat_view.py:946-962`

**原问题**：`on_leave` 未取消 `_delta_update_timer`，可能在视图离开后触发冗余 `page.update()`

**修复**：`on_leave` 调用 `_reset_streaming_state()`（含取消定时器）

---

### REG-6 · 程序滚动期间按钮闪烁 ✅

**定位**：`app/views/chat_view.py:259-262`

**原问题**：`_program_scroll` 仅守护 `_user_scrolled`，未守护 `auto_scroll` 切换与按钮同步 → 200ms 动画期间按钮闪烁

**修复**：`auto_scroll` 切换 + `_sync_bottom_btn` 两行用 `if not self._program_scroll:` 包裹

---

### REG-LOGIC-1 · _on_msg_end row-is-None 递减计数错乱 ✅

**定位**：`app/views/chat_view.py:702-706`

**原问题**：`_on_streaming_start` 对空 msg_id 不递增，但 `_on_msg_end` row is None 时仍递减 → 计数不对称，msg_end 重复 emit 时会错减别人的计数

**修复**：row is None 时不递减（仅 `_streaming_rows` 内的才递减）

---

### REG-LOGIC-3 · start() invariant 与孤儿检测语义冲突 ✅

**定位**：`core/dialogue_loop.py:74`

**原问题**：`invariant(not self.running, ...)` 声明不应在运行时调用，但下方孤儿检测正是处理运行中重启 → 每次打印误导警告

**修复**：移除该 invariant，孤儿检测逻辑统一处理

---

### REG-LOGIC-4 · 日志打印 httpx.Timeout 对象 ✅

**定位**：`services/api_service.py:224`

**原问题**：timeout 转为 `httpx.Timeout` 对象后，日志打印 `timeout=Timeout(connect=10.0, ...)` 而非可读数字

**修复**：提取 `timeout.read` 用于日志

---

## 阶段 2 已修复的 Bug

### P1-9 · 长按菜单使用不存在的 Flet API → 移动端长按完全无响应 ✅

**定位**：`app/views/profiles_view.py:738-774`

**原问题**：`page.show_bottom_sheet(sheet)` / `page.close_bottom_sheet()` 在 Flet 0.86 不存在（已验证 `hasattr` 返回 False）→ 长按卡片无任何反应，`AttributeError` 被 try/except 吞掉

**修复**：
1. `_show_card_menu_sheet` 改用 `page.overlay.append(sheet); sheet.open=True; page.update()`
2. `_close_sheet` 改用 `sheet.open=False` + `page.overlay.remove(sheet)`
3. 保留 ⋮ PopupMenuButton 作为桌面端替代入口（双入口冗余）
4. 加 `on_dismiss=lambda e: self._close_sheet()` 处理遮罩 dismiss 路径（修复回归 BUG-8：overlay 孤儿泄漏）
5. 开头加 `if self._opened_sheet: self._close_sheet()` 清理前一个残留 sheet

---

### P1-10 · profiles_view 无 on_leave + save_and_switch 无超时 ✅

**定位**：`app/views/profiles_view.py:635-687`

**原问题**：`save_and_switch` 订阅 saving/saved 用局部闭包，AI 标题挂起时对话框永久挂死；profiles_view 无 on_leave，闭包订阅永远挂在 bus 上 → 跨视图 saved 事件串扰

**修复**：
1. 新增 `on_leave`：清理保存订阅 + 关闭保存对话框 + 关闭 sheet + 置标志
2. `save_and_switch` 内部闭包改为实例方法 `_on_save_saving`/`_on_save_saved`/`_unsubscribe_save_events`
3. 加 30s+30s 超时兜底：30s 时 `fail("保存超时", on_close=_on_timeout_close)`，用户 dismiss 后置 `_save_switch_done=True`；60s 后仍未完成则强制清理+切换
4. `_on_save_saved` 的 `on_close` lambda 加 `if self._save_switch_folder is not None` 守卫（修复回归 BUG-4：用户离开后仍强制切换）
5. 加代际令牌 `_save_generation` 隔离旧超时线程（修复回归 BUG-2：跨保存串扰）

---

### P1-11 · 非活跃剧本详情页改名会破坏活跃剧本的内存 history ✅

**定位**：`app/views/profiles_view.py:428-431, 540-543`

**原问题**：`load_profile_for_edit` 不交换 history，改名代码操作 `self.state.history`（活跃剧本 A 的）→ A 的 history 中 Lin 被错误改名为 Lin2

**修复**：改名迁移 history 前检查 `editing_folder == active_folder`，仅当编辑的剧本是活跃剧本时才迁移内存 history；磁盘存档迁移 `_migrate_character_in_chats` 用 `self.state.profile_dir`（=编辑剧本）始终正确

---

### P1-12 · archives_view 保存超时把"已成功"对话框误覆盖为"超时失败" ✅

**定位**：`app/views/archives_view.py:381-389`

**原问题**：超时线程只检查 `if self._save_dialog:`，未检查"保存是否已完成"→ 28s 时 _on_saved 成功显示"保存成功"，30s 时超时覆盖为"超时失败"

**修复**：
1. 新增 `_save_completed` 标志，`_on_saved` 成功后置 True
2. 超时线程 30s 时检查 `if self._save_completed: return`，不覆盖已成功的对话框
3. 加 `_saving` 防抖（修复 P2-L3：双击孤立对话框 + 事件重复订阅泄漏）
4. 加代际令牌 `_save_generation` 隔离旧超时线程（修复回归 BUG-3：跨保存串扰）
5. `on_leave` 关闭 `_save_dialog` + 置标志 + bump 代际（修复 P2-L4：跨视图悬挂 + 超时误弹）

---

### P2-L1 · settings_view.on_enter 调 load_profile 重置场景上下文 ✅

**定位**：`app/views/settings_view.py:397-404`

**原问题**：`on_enter` 调 `load_profile(active)` 会无条件重置 `current_scene=None, scene_idx=0` → 用户从剧本页回设置页再回聊天页时场景上下文丢失

**修复**：改用 `load_profile_for_edit(active)`（保存/恢复运行时场景状态）；`_color_theme_dd.value` 设置后加 `.update()`

---

### P2-W1 · _try_focus 对 coroutine 调 close() → Web 端焦点不生效 ✅

**定位**：`app/components/director_input.py:162-168`

**原问题**：Flet Web 模式下 `focus()` 返回 coroutine，调 `result.close()` 会丢弃协程 → 焦点不生效（移动端键盘不弹出）

**修复**：
1. `__init__` 捕获 `_async_loop`（仿 TransportBar/ProgressDialog 模式，主线程构造时获取）
2. `_try_focus` 用 `asyncio.run_coroutine_threadsafe(result, self._async_loop)` 跨线程安全调度（EventBus 在后台线程触发）
3. 删除 `get_event_loop` 废弃调用和重复 except 死代码（修复回归 BUG-6）

---

### P2-W2 · transport_bar.set_running 未用 async-safe 路径 ✅

**定位**：`app/components/transport_bar.py:129-132`

**原问题**：`set_running` 从后台线程（EventBus 事件）直接 `page.update()`，Web 端可能更新丢失

**修复**：`__init__` 捕获 `_async_loop`；`set_running` 用 `call_soon_threadsafe`（与 chat_view._push_update 一致）

---

## 阶段 2 回归修复

### REG-S2-1 · profiles_view 60s 超时线程在用户 dismiss 超时对话框后仍强制切换 ✅

**定位**：`app/views/profiles_view.py:669-688`

**原问题**：30s 的 `fail()` 不带 `on_close`，用户 dismiss 超时对话框后 `_save_dialog` 仍非 None，60s 后旧线程强制切换 → 用户被拉回 /chat + history 被清空

**修复**：30s 的 `fail()` 带 `on_close=_on_timeout_close`，回调内置 `_save_dialog=None` + `_save_switch_done=True` + unsubscribe

---

### REG-S2-2/3 · on_leave 重置完成标志为 False 导致旧超时线程复活 ✅

**定位**：`app/views/profiles_view.py:1196` + `app/views/archives_view.py:604`

**原问题**：`on_leave` 把 `_save_switch_done=False` / `_save_completed=False`，旧超时线程 60s 后看到 False → 复活强制切换/误 fail 新对话框

**修复**：改为置 `True`（向旧线程发"已结束"信号）+ bump `_save_generation` 代际令牌

---

### REG-S2-4 · on_close lambda 缺守卫 → 用户离开后 dismiss 仍强制切换 ✅

**定位**：`app/views/profiles_view.py:743, 748`

**原问题**：`complete(on_close=lambda: self._do_switch_and_enter(folder))` 无守卫，用户离开后 800ms 自动关闭仍触发切换

**修复**：lambda 加 `if self._save_switch_folder is not None else None` 守卫，`on_leave` 置 `_save_switch_folder=None`

---

### REG-S2-6 · _try_focus 在后台线程调用 get_running_loop 必失败 ✅

**定位**：`app/components/director_input.py:162-186`

**原问题**：`_try_focus` 在调用时才 `get_running_loop()`，但 EventBus 事件由对话 loop 后台线程 emit → 该线程无 running loop → RuntimeError → 协程被丢弃 → Web 端"轮到你了"焦点仍失效

**修复**：`__init__` 捕获 `_async_loop`（主线程构造时），`_try_focus` 用捕获的 loop 调 `run_coroutine_threadsafe`

---

### REG-S2-8 · BottomSheet 遮罩 dismiss 路径 overlay 孤儿泄漏 ✅

**定位**：`app/views/profiles_view.py:738-774`

**原问题**：用户点击遮罩区域 dismiss sheet 时，Flet 自动设 `open=False` 但代码未监听 `on_dismiss`，sheet 永久留在 `page.overlay`

**修复**：sheet 加 `on_dismiss=lambda e: self._close_sheet()`；`_show_card_menu_sheet` 开头先清理前一个残留 sheet

---

## 阶段 3 待修复 Bug

### P1-8 · speed 速度控制完全失效（暂不修，低优先级）

**定位**：`core/dialogue_loop.py:457-464`

**原问题**：`_paused.wait(0.1)` 在未暂停时立即返回（Event.wait 语义是"等到 set 或超时"），循环空转 → speed=1 和 speed=10 速度一样

**修复方向**：改用 `time.sleep(0.1)` 或 `_stop_event.wait(0.1)`（`_stop_event` 在运行时未 set → 会真正等待超时）

**用户决策**：暂不修，API 延迟自然间隔掩盖了问题

---

### P1-9 · 长按菜单使用不存在的 Flet API → 移动端长按完全无响应

**定位**：`app/views/profiles_view.py:768, 772`

**原问题**：`page.show_bottom_sheet(sheet)` / `page.close_bottom_sheet()` 在 Flet 0.86 不存在（已验证 `hasattr` 返回 False）→ 长按卡片无任何反应，`AttributeError` 被 try/except 吞掉

**修复方向**：改用 `page.overlay.append(sheet); sheet.open=True; page.update()`；保留 ⋮ 按钮作为桌面端替代入口

---

### P1-10 · profiles_view 无 on_leave + save_and_switch 无超时 → 对话框挂死 + 事件泄漏

**定位**：`app/views/profiles_view.py:635-687`（类无 on_leave）

**原问题**：`save_and_switch` 订阅 saving/saved 用局部闭包，AI 标题挂起时对话框永久挂死；profiles_view 无 on_leave，闭包订阅永远挂在 bus 上 → 跨视图 saved 事件串扰

**修复方向**：profiles_view 加 on_leave 清理订阅 + save_and_switch 加 30s 超时

---

### P1-11 · 非活跃剧本详情页改名会破坏活跃剧本的内存 history

**定位**：`app/views/profiles_view.py:428-431, 540-543`

**原问题**：`load_profile_for_edit` 不交换 history，改名代码操作 `self.state.history`（活跃剧本 A 的）→ A 的 history 中 Lin 被错误改名为 Lin2

**修复方向**：改名前检查 `folder == config.app_config["active_profile"]`，活跃剧本的 history 操作跳过

---

### P1-12 · archives_view 保存超时把"已成功"对话框误覆盖为"超时失败"

**定位**：`app/views/archives_view.py:381-389`

**原问题**：超时线程只检查 `if self._save_dialog:`，未检查"保存是否已完成"→ 28s 时 _on_saved 成功显示"保存成功"，30s 时超时覆盖为"超时失败"

**修复方向**：超时前检查 `_save_dialog._closed`（已 complete 则不覆盖）

---

## 阶段 2-3 待修复的 P2/P3 bug

详见前两轮 BUG_REPORT.md / BUG_REPORT_2.md 及本轮分析附录。重点：

- **P2-L1**：settings_view.on_enter 调 load_profile 重置场景上下文 → 对话场景丢失
- **P2-L2/L3/L4**：三视图保存订阅生命周期不一致导致总线串扰
- **P2-W1**：_try_focus 对 coroutine 调 close() → Web 端焦点不生效
- **P2-W2**：transport_bar.set_running 从后台线程 page.update() 未用 async-safe 路径
- **P2-M1/M2/M3/M4**：移动端导出/长按/拖拽的跨平台 UI 差异
- **P3-1**：流式期间回到底部按钮完全不出现（过度抑制）
- **P3-2**：用户回合点 PLAY 无视觉反馈
- **P3-7**：strip_streaming_tags 在 token 边界闪烁

---

## 附录 · 已确认的正常行为（修改时勿误伤）

继承前两轮报告的全部确认正常行为，新增：

16. **`_user_scrolled` 标志的设置时机**：程序滚动（_scroll_to_bottom）期间 `_program_scroll=True` 守护，用户主动上滚时置 True，回到底部时清除。修改时注意 `_program_scroll` 的 0.4s Timer 清除时机。
17. **`_schedule_delta_update` 的 100ms 节流**：合并多次 delta update 为一次，`_finalize_msg_end` 取消挂起定时器并立即 push 最终内容。修改时注意定时器与 finalize 的竞态（已在阶段 1 回归分析中确认低风险）。
18. **`stop_check` 的 SSE 行间触发限制**：无法在 `iter_lines()` 阻塞期间触发，最长需等 read timeout（120s）。阶段 2 计划保存 httpx Client 句柄实现强关。

---

## 附录 · 阶段 1 修改的文件清单

| 文件 | 修改内容 |
|---|---|
| `services/api_service.py` | 新增 StreamInterrupted 异常；call_chat_completion_stream 加 stop_check + SSE 解析容错 + timeout 分离；async 版透传 stop_check |
| `core/ai_engine.py` | 新增 _stop_check 方法；三个流式函数透传 stop_check |
| `core/dialogue_loop.py` | start() 加孤儿线程检测；_stream_npc_dialogue 重构 try/except/finally 保证 msg_end + farewell 清理 |
| `app/views/chat_view.py` | 新增 _user_scrolled/_program_scroll/_delta_update_timer；_on_scroll 区分用户/程序滚动；_on_msg_delta/_on_msg_end 尊重用户滚动 + update 节流；_reset_streaming_state 清理流式状态；on_leave 调用清理 |
| `config.py` | 移除 import-time 复制；API_VERIFY_SSL/API_TRUST_ENV 从 app_config["network"] 读取 |
| `services/path_resolver.py` | get_data_dir Android/iOS 兜底；setup_workspace 原子复制 + 重新加载 + _sync_config_from_app_config；新增 _ensure_dev_config |
| `app/views/settings_view.py` | API 卡片新增 SSL/代理开关 + _on_network_change + _sync_api_fields 同步 |

**报告结束。**
