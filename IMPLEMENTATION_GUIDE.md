# ChatRoom Flet 版 · UI 实现指南

> 本文档供新 opencode 会话使用。环境搭建 + 数据迁移 + core 业务层已完成,
> 剩余工作是 **纯 Flet UI 实现**。把本文档连同 `dorm-flet/` 项目交给新 AI 即可开工。

---

## 1. 当前项目状态

### 已完成(勿重复造轮子)

| 层级 | 文件 | 说明 |
|---|---|---|
| **配置** | `config.py` | 全局配置/路径/字体路径/随机事件默认参数。零 Kivy 依赖 |
| **工具** | `utils.py` | `load_json`/`save_json`/`hex_to_rgba`/`extract_json`。已删除 Kivy 的 `make_popup_label` |
| **服务层** | `services/api_service.py` | LLM HTTP 封装。同步/异步/测试连接/拉模型列表。已删除 `kivy.clock` |
| **服务层** | `services/path_resolver.py` | 平台路径抽象(桌面/Android/iOS/Web) |
| **业务层** | `core/events.py` | `EventBus` —— 替代 Kivy 的 `Queue + Clock.schedule_interval(poll_queue)` |
| **业务层** | `core/ai_engine.py` | prompt 构建/LLM 调用/动态选人/随机事件/NPC/时间场景生成/标签解析。零 UI 依赖 |
| **业务层** | `core/chat_manager.py` | 存档读写/AI 标题生成/自动存档/启动恢复。UI 弹窗代码已删除,改发 EventBus 事件 |
| **业务层** | `core/data_manager.py` | profile 加载/迁移/CRUD/角色管理。已删除 `welcome_title`/`welcome_text` 字段 |
| **业务层** | `core/dialogue_loop.py` | 从 `main.py _run_loop/_handle_cmd` 抽出的纯线程循环。通过 EventBus 通知 UI |
| **业务层** | `core/app_state.py` | ★ 中心状态对象 `AppState`,聚合所有业务层,UI 层只需持有一个实例 |
| **数据** | `profiles/` | 从旧项目复制,JSON 格式 100% 向后兼容(dorm_life/starship 两个剧本) |
| **数据** | `config.json`/`config.example.json` | API 配置 |
| **资源** | `assets/NotoSansSC-Regular.ttf` | 中文字体(供 Flet `page.fonts` 注册) |
| **环境** | `dorm-flet-venv` | 已装 flet 0.85.3 + httpx 0.28.1 |

### 待实现(你的工作)

```
app/
├── theme.py              # Soft Twilight M3 主题 + 浅/深色切换
├── router.py             # 路由 / 响应式导航(NavigationRail/Bar)
├── state.py              # UI 反应式状态(当前路由/主题模式/对话框等)
├── main_app.py           # ft.app 入口,组装 AppState + 主题 + 路由
├── views/
│   ├── chat_view.py      # 主聊天页
│   ├── profiles_view.py  # 剧本库 + 剧本详情
│   ├── archives_view.py  # 对话存档
│   └── settings_view.py  # 设置(API/默认行为/外观/关于)
└── components/
    ├── chat_bubble.py        # 气泡(无尾巴卡片)
    ├── scene_banner.py       # 场景横幅
    ├── mode_chips.py         # 模式 Chip 组
    ├── transport_bar.py      # 开始/暂停/停止/速度工具条
    ├── director_input.py     # 底部输入栏
    ├── character_card.py     # 角色卡
    ├── profile_card.py       # 剧本封面卡
    └── reorderable_list.py   # 拖拽排序列表(Draggable+DragTarget)
main.py                   # 入口脚本: ft.run(app.main_app.main)
```

---

## 2. core 层 API 速查(UI 实现时直接调用)

### 2.1 AppState(中心入口)

```python
from core.app_state import AppState

state = AppState()
state.init_workspace()              # 启动时调用:路径初始化+迁移+加载默认剧本
state.check_autosave_on_start()     # 启动后调用:检测自动存档

# 剧本
state.load_profile("dorm_life")
state.switch_profile("starship")
state.data.get_profile_list()                       # → ["starship", "dorm_life"]
state.data.profile_name_to_display("dorm_life")     # → "ChatRoom"
state.data.create_profile("魔法学院")               # → folder_name
state.data.delete_profile("starship")               # → bool
state.data.rename_profile("dorm_life", "新名字")    # → bool

# 场景
state.scenes                        # list of {time, location, scene, mood}
state.scene_idx                     # int, -1 表示"按时间生成"
state.current_scene                 # dict 或 None(动态场景)
state.loop.prev_scene() / next_scene()  # 手动切换场景,会发 "scene_changed" 事件

# 角色
state.characters                    # {name: {name, display_name, system_prompt, ...}}
state.char_styles                   # {name: {color, bg, name}}
state.data._save_character(filename, data)
state.data._delete_character(name)
state.data._reload_data()

# 发言顺序
state.turn_order                    # list of name
state._get_effective_order()        # 当前模式有效顺序(用户模式含 You)
state.data._save_turn_order()

# 对话控制
state.loop.start()                  # 启动(会先检查 API Key,发 "api_error_stop" 若无)
state.loop.pause()
state.loop.resume()
state.loop.stop()                   # 停止,保留 history
state.loop.reset()                  # 停止并清空
state.loop.set_speed(5)
state.loop.set_mode("dynamic")      # round | random | dynamic
state.loop.send_director_note("突然有人敲门")
state.loop.send_user_message("大家好")
state.loop.skip_user_turn()

# 对话存档
state.chat.save_current_chat()                       # 触发 AI 标题生成,发 "saving"/"saved" 事件
state.chat.load_chat(path)                           # → bool
state.chat.delete_chat(path)                         # → bool
state.chat.list_chats_with_meta()                    # → [(path, meta), ...]
state.chat.has_unsaved_messages()                    # → bool
state.chat.restore_autosave(path)                    # → bool
state.chat.discard_autosave(path)
state.chat._auto_save()                              # 静默自动存档
state.auto_save()                                    # 同上(便捷封装)

# 模式开关
state.director_mode / user_mode / dynamic_scene_enabled / random_event_enabled  # bool
# 修改后需持久化:
state.data._save_profile_config()

# 时间场景生成(scene_idx == -1 时)
state.ai.generate_time_scene_sync()    # → (scene_dict, error) 同步调 LLM
state.ai._get_time_label()             # → "午后"/"深夜" 等

# API 配置(设置页)
import config
config.API_KEY / API_BASE / MODEL / TEMPERATURE / MAX_TOKENS
config.app_config["model"] = {...}     # 修改后调 state.data._save_config() 持久化
from services.api_service import test_connection_async, fetch_models_async
test_connection_async(on_result=lambda ok, msg: ...)    # ok: bool, msg: str
fetch_models_async(on_result=lambda models: ...)        # models: list[str]
```

### 2.2 EventBus 事件清单(UI 层用 `state.bus.on(event, handler)` 订阅)

| 事件 | 触发时机 | data |
|---|---|---|
| `"msg"` | 新角色/导演/用户消息 | `entry = {name, display_name, text, time, type?}` |
| `"random_event_msg"` | 随机事件 | `entry = {name:"__random__", display_name:"随机事件", text, time, type:"random_event"}` |
| `"random_npc_msg"` | 路人 NPC 消息 | `entry = {..., type:"random_npc", is_farewell?}` |
| `"user_turn"` | 轮到用户发言 | `None`(UI 显示输入栏) |
| `"set_status"` | 状态栏更新 | `str`("运行中"/"已暂停"/"轮到你了～"等) |
| `"scene_changed"` | 场景切换 | `{time, location, scene, mood, version, manual?, is_time_gen?}` |
| `"api_error_stop"` | API 连续失败 | `str`(错误消息) |
| `"started"` | 对话启动 | `None` |
| `"paused"` | 对话暂停 | `None` |
| `"resumed"` | 对话恢复 | `None` |
| `"stopped"` | 对话停止 | `None` |
| `"saving"` | 正在保存对话 | `None`(UI 显示进度) |
| `"saved"` | 保存完成 | `{title, success, message, path}` |
| `"autosave_prompt"` | 启动检测到自动存档 | `{title, message_count, path}` |

### 2.3 消息类型对照(气泡渲染依据)

| `entry.type` | 渲染 |
|---|---|
| 无(普通) | AI 角色:左对齐,角色色头像,`surface_container_low` 气泡 |
| 无 + `entry.name == "You"` | 用户扮演角色:右对齐,primary 头像,`primary_container` 气泡 |
| `"director"` | 导演:右对齐,amber 头像,amber_container 气泡,带"导演"tag |
| `"random_event"` | 随机事件:居中,无头像,`outline` 色文字,"🎲 随机事件" 分割线 |
| `"random_npc"` | 路人 NPC:左对齐,amber 头像,带"路人"tag;`is_farewell=True` 时可灰显 |

---

## 3. UI 设计规格(完整预览)

### 3.0 设计语言:Soft Twilight 暮光

| 维度 | 规格 |
|---|---|
| 主色种子 | Indigo-Violet `#6366F1`,M3 自动派生 40 色 tonal palette |
| 强调色 | 暖琥珀 `#F59E0B`(导演/高亮)、玫瑰 `#F43F5E`(停止/危险)、青绿 `#10B981`(运行/成功) |
| 气泡角色色 | 每个角色一个 hue(种子色 + HSL 偏移),头像圆+名字+气泡统一色 |
| 圆角 | 卡片 16px、气泡 16px(**无尾巴,四角统一**)、Chip/按钮 pill(全圆) |
| 海拔 | 弃用重阴影,用 M3 tonal surface(`surface_container_low/high`);FAB/弹窗用 0.5dp 软影 |
| 字体 | Noto Sans SC(注册为 `page.fonts`);标题 22/16、正文 14/13、辅助 12;字重 500/700 |
| 间距 | 4/8/12/16/24/32 网格 |
| 动效 | 气泡 `slide_in_up + fade` 250ms、Chip 切换 `scale 0.95→1` 150ms、场景横幅滑入 300ms |
| 主题 | 浅色/深色/跟随系统 三态 |

### 3.1 应用框架(响应式)

**桌面/平板(width ≥ 900)**:左侧 `NavigationRail`(宽 72px,4 项:聊天/剧本/存档/设置),右侧内容区。

**手机(width < 900)**:顶部 `AppBar`,底部 `NavigationBar`(4 项),`page.adaptive=True` 让 iOS 自动切 Cupertino 风格。

导航项:
- 💬 聊天 → `/chat`
- 📚 剧本 → `/profiles`
- 🗂️ 存档 → `/archives`
- ⚙️ 设置 → `/settings`

### 3.2 聊天视图(主界面)

**空状态(未开始)**:
- 居中大 emoji/插画
- **剧本标题**(Text 22 bold)——注意:**不再显示欢迎标题/欢迎文字**,只显示 `state.title`
- "参与角色" 分割线 + 角色头像行(`CircleAvatar` 14px + 名字)
- 居中 `FilledButton("▶ 开始对话")` pill
- 底部场景选择 Banner(`📍 午后 · 客厅 ✕`)

**运行中**:
- AppBar:左暂停快捷,中间"剧本名 · 场景",右主题切换 + 设置
- **模式 Chip 组**:`[导演][用户][动态场景][随机事件]`(选中=filled,未选=outline)
- 聊天区:气泡列表(见 §2.3 类型对照)
- **TransportBar**:`轮流 ▾` Dropdown + `速度 ━●━━ 3` Slider + `▶ ⏸ ⏹` 三按钮 + `💾`(暂停时显示)
- **导演/用户输入栏**:仅导演/用户模式时滑入,`TextField` + `发送` 按钮(用户模式多一个`跳过`)
- 状态栏:`● 运行中 · 第 8 轮    42 条 ▼`(状态点+轮次+消息数+回底按钮)

**气泡(无尾巴卡片)**:
- AI 角色:左对齐,`Row[CircleAvatar14, Column[Name+Time, Container(气泡)]]`,气泡 `border_radius=16`,bg=`surface_container_low`
- 用户角色:右对齐,气泡 bg=`primary_container`,文字=`on_primary_container`
- 导演:右对齐,amber 头像,气泡 bg=amber 浅色,带"导演"tag pill
- 随机事件:居中,无头像,`── 🎲 随机事件 ──` 分割线 + italic 文字
- 路人 NPC:左对齐,amber 头像 + "路人"tag,气泡 border=amber 1px
- 场景切换:居中 Banner,`📍 场景切换` + 场景文本,2.5s 自动收起

**AppBar 下拉**(点剧本名 `▾`):`Menu` 切换剧本 + 切换场景(含"⏱ 按现实时间生成")

### 3.3 剧本库视图

- AppBar:`剧本库` + `+ 新建`(FilledTonalButton) + `✨ AI 创建`(FilledButton)
- **卡片网格**(每行 2 列手机 / 3-4 列桌面):
  - 封面 120px:剧本主色渐变 + 代表性 emoji 大字(寝室日常🏠 / 星际飞船🚀)
  - 信息:标题 / `N角色·M场景` badges / 世界观 2 行 / `K 个存档`
  - `Card(border_radius=16, tonal bg)`
  - 长按/右键菜单:重命名/复制/删除/导出
- AI 创建按钮弹多步对话框(见 §3.7)

### 3.4 剧本详情(进入卡片后)

顶部 `SegmentedButton` 切 5 分区(手机)或左侧二级 NavigationRail(桌面):
`[概览][场景][角色][发言][随机]`

**概览**:应用标题 TextField / 世界观 TextField(multiline=4)+ `[✨ AI推断]` / 剧本主色色板选择
(注意:**不再有欢迎标题/欢迎文字字段**)

**场景**:ListTile 列表,每条 `☰ 拖拽手柄 + 时间·地点 + 描述 + ⋮菜单(编辑/删除/AI补全)`,顶部 `+ 添加` + `✨ AI 生成`

**角色**:卡片网格,每张 `CircleAvatar(色点+首字) + 名字 + 英文名 + 描述2行 + [✨补全][⋮]`,另含`+ 新角色`卡 + `✨ AI 生成`卡

**发言顺序(拖拽)**:
- `轮流模式 ▾` Dropdown(轮流/随机/动态)
- ▼ 参与对话:`Draggable+DragTarget` 列表,每行 `☰ ●名字 [✕]`,拖拽时半透明+accent虚线
- ▼ 待命角色:`OutlinedChip` 点+加入
- 🔒 你(用户模式自动加入,锁定)

**随机**(注意:**仅作为开关,无参数配置 UI**):
- `随机事件引擎 [● 开启]` Switch
- 简短说明文字:"启用后,对话中会自动注入意外事件或路人 NPC"
- 当前状态显示(只读):`● 运行中 · NPC「快递员」活跃` 或 `未启用`

### 3.5 对话存档视图

- AppBar:`对话存档 · 剧本名` + `[💾 保存当前]` + `[📋 复制全部]`
- 按日期分组(`── 今天 ──` / `── 昨天 ──`)
- 每条 ListTile:`标题(AI生成)` + 预览 + 消息数 + `[读取][⋮]`
- 自动存档条目置顶,amber 容器 + ⚡ 图标 + "自动存档"tag

### 3.6 设置视图

分区卡片:
- **API 配置**(顶部,带状态点 ●已连接/●未配):
  - API 地址 TextField / API Key TextField(password + 👁显隐) / 模型 Dropdown + `[刷新模型列表]` / 温度 Slider / 最大 tokens Slider / `[测试连接]` + `[保存]`
  - 测试连接显示 ProgressIndicator → 成功绿 `✓ 连接正常,延迟 Xms` / 失败红 `✗ 错误`
- **外观**:主题模式 RadioGroup(浅色/跟随系统/深色) / 主题色色板(8预设+自定义) / 字体大小 Slider
- **默认行为**:导演/用户/动态场景/随机事件 Switch × 4 / 默认发言模式 Dropdown / 默认速度 Dropdown
- **关于**:版本 / GitHub / 问题反馈 / 许可证

### 3.7 关键弹窗

**AI 一键创建剧本**(三步同 dialog):
1. 输入:`TextField(multiline)` + 示例提示 + `[取消][开始生成]`
2. 生成中:`✓ 世界形 / ✓ 场景1·2·3 / ⏳ 角色1 / ○ 角色2·3·你` + `ProgressBar 5/10`
3. 完成:`已生成:N角色·M场景` + `[进入剧本][再改改]`

**停止确认**:`⚠ 当前对话有 N 条未保存消息` + `[保存并停止][直接停止][取消]`

**时间场景预览**:`📍 场景预览` + 场景文本 + `[换一个][开始对话]`

**自动存档恢复**(启动时):`检测到上次未保存的对话「标题」N条消息,是否恢复?` + `[恢复][放弃]`

### 3.8 主题色对照

**浅色**:
- surface `#FAF9FF`(微紫白)/ primary `#6366F1` / bubble(AI) `#F0F1FE` / bubble(我) `#E0E1FE` / director `#FEF3C7` / text `#1A1B2E`

**深色**:
- surface `#121218` / primary `#818CF8`(提亮)/ bubble(AI) `#1E1F2E` / bubble(我) `#2A2C42` / director `#3D3520` / text `#E6E7F0`

### 3.9 微交互

| 场景 | 动效 |
|---|---|
| 新气泡进入 | `slide_in_up 250ms + fade`,自动滚到底 |
| 模式 Chip 切换 | `scale 0.92→1 150ms` + 颜色 fade |
| 场景横幅 | 滑入 300ms,2.5s 后滑出 |
| 拖拽排序 | 源行 `opacity 0.4`,目标位 accent 虚线 + scale 1.02 |
| 暂停按钮 | `pulse` 呼吸动画 |
| AI 生成中 | `ProgressIndicator` + 完成项 checkmark pop |
| 主题切换 | 全局 `fade 200ms` |
| 回底按钮 | 滚动远离底部时 `scale 0→1` 弹出 |

---

## 4. 实现步骤建议

按此顺序,每步完成后 `flet run main.py` 验证:

### Step 1: 脚手架与主题
- `app/theme.py`:`build_theme(mode)` 返回 `ft.Theme(color_scheme_seed=#6366F1)`,配置浅/深色
- `main.py`:`ft.run(main)`,`main(page)` 注册字体 `page.fonts={"Noto Sans SC": "assets/NotoSansSC-Regular.ttf"}`,设置 `page.theme`/`page.dark_theme`/`page.theme_mode`,创建 `AppState` 并调 `init_workspace()`
- 验证:空白窗口能显示,字体生效

### Step 2: 响应式导航与路由
- `app/router.py`:用 `page.on_route_change` 或 0.85 的 `ft.Router` 实现 4 视图切换
- 桌面 `NavigationRail` / 手机 `NavigationBar`(用 `page.on_resize` 或 `page.width` 判断)
- 4 个空视图占位
- 验证:切换视图/响应式布局正常

### Step 3: 聊天视图骨架
- `app/views/chat_view.py`:AppBar + 模式 Chip 组 + 空列表 + TransportBar + 状态栏
- `app/components/mode_chips.py`:`[导演][用户][动态场景][随机事件]` Chip 组,绑定 `state.xxx_mode` 开关
- `app/components/transport_bar.py`:Dropdown + Slider + 三按钮,绑定 `state.loop.start/pause/stop`
- 验证:模式开关切换、开始/暂停按钮触发(无 API Key 时应弹提示)

### Step 4: 气泡渲染 + EventBus 接入
- `app/components/chat_bubble.py`:按 §2.3 类型对照渲染气泡(无尾巴卡片)
- 在 chat_view 订阅 `state.bus.on("msg", ...)`,`"random_event_msg"`,`"random_npc_msg"`,`"set_status"`,`"scene_changed"`,`"user_turn"`,`"started"/"paused"/"resumed"/"stopped"`
- 新气泡进入时滚动到底 + 动效
- 验证:配置 API Key 后 `state.loop.start()` 能看到气泡流入

### Step 5: 场景横幅 + 输入栏
- `app/components/scene_banner.py`:场景横幅,监听 `"scene_changed"` 事件,2.5s 自动收起
- `app/components/director_input.py`:底部输入栏,导演/用户模式时滑入
- 验证:导演提示能注入、用户回合能输入/跳过

### Step 6: 剧本库 + 详情
- `app/views/profiles_view.py`:卡片网格 + `profile_card.py`
- 剧本详情:5 分区(概览/场景/角色/发言/随机)
- `app/components/reorderable_list.py`:拖拽排序(`Draggable`+`DragTarget`,`on_accept` 交换 `state.turn_order` 后 `_save_turn_order()`)
- AI 创建剧本弹窗(三步)
- 验证:切换剧本、编辑角色、拖拽排序、AI 创建

### Step 7: 对话存档
- `app/views/archives_view.py`:分组列表 + 保存/读取/删除/重命名
- 订阅 `"saving"`/`"saved"`/`"autosave_prompt"` 事件显示弹窗
- 验证:保存/读取/启动恢复

### Step 8: 设置
- `app/views/settings_view.py`:API 配置 + 外观 + 默认行为 + 关于
- API 测试连接(`test_connection_async`)
- 主题切换(浅/深/跟随系统)
- 验证:API 配置持久化、主题切换、测试连接

### Step 9: 打包
- `flet build apk`(Android)/ `flet build ios`(iOS)/ `flet build web`(Web)/ `flet build exe`(Windows)

---

## 5. 关键技术点

### 5.1 EventBus 订阅时机
- UI 视图初始化时 `state.bus.on(event, handler)` 订阅
- 视图卸载时 `state.bus.off(event, handler)` 取消(防止重复订阅)
- 或在 `AppState` 创建后立即订阅全局事件(状态栏等)

### 5.2 跨线程安全
- Flet 的 `page.update()` 是跨线程安全的,EventBus handler 在后台线程触发时可直接 `control.value = ...; control.update()`
- **无需 Kivy 的 `@mainthread` 或 `Clock.schedule_once`**

### 5.3 字体注册
```python
page.fonts = {"Noto Sans SC": "assets/NotoSansSC-Regular.ttf"}
page.theme = ft.Theme(font_family="Noto Sans SC")
```
**emoji 与图标**:Flet 内置 Material/Cupertino 图标字体(`ft.Icons.*`),emoji 文字(`Text("🎲")`)也开箱即用,**无需手动注册任何字体文件**(这是 Kivy 版的主要痛点,Flet 已解决)。

### 5.4 拖拽排序实现
```python
# 每个列表项:
ft.DragTarget(
    group="order",
    content=ft.Draggable(
        group="order",
        content=item_card,
        content_when_dragging=ft.Container(opacity=0.4, content=item_card),
        data=item_index,
    ),
    on_will_accept=lambda e: highlight_border(e),
    on_accept=lambda e: swap_items(e.src.data, target_index, state),
)
```
`swap_items` 中交换 `state.turn_order` 列表,重建 ListView,调 `state.data._save_turn_order()`。

### 5.5 剧本封面 emoji 映射
```python
PROFILE_EMOJI = {
    "dorm_life": "🏠", "starship": "🚀",
    # 无匹配时用 📖 或根据标题关键词推断
}
```
也可让 AI 创建剧本时返回一个 `emoji` 字段存入 profile config。

### 5.6 主题切换
```python
THEME_MODES = {"light": ft.ThemeMode.LIGHT, "dark": ft.ThemeMode.DARK, "system": ft.ThemeMode.SYSTEM}
page.theme_mode = THEME_MODES[mode]
# 持久化到 config.app_config["ui"]["theme_mode"]
```

### 5.7 生命周期(自动存档)
- 桌面:`page.on_window_event`(监听 `close`)→ `state.auto_save()`
- Web:`page.on_disconnect` → `state.auto_save()`
- Android:用 `page.on_window_event` 或 Flet 的 mobile 生命周期钩子

---

## 6. 启动方式

```bash
# 激活 venv
source ~/dorm-flet-venv/bin/activate

# 进入项目
cd ~/dorm-flet

# 桌面预览
flet run main.py

# 指定端口 Web 预览
flet run main.py --web --port 8080

# Android(需连接设备)
flet build apk

# iOS
flet build ios

# Web 部署
flet build web
```

---

## 7. 用户已确认的变更(相对旧项目)

1. **移除随机事件设置窗口**:随机事件仅作为剧本详情里的 Switch 开关,无参数配置 UI(参数用 `config.RANDOM_EVENT_DEFAULTS` 内置默认值:冷却3/斜坡10/概率0.35/事件偏向0.5)
2. **移除欢迎标题与欢迎文字**:空状态只显示剧本标题(`state.title`);profile config 的 `welcome_title`/`welcome_text` 字段废弃
3. **移除 AI 生成欢迎语**:相关 prompt builder 已删除
4. **气泡完全无尾巴**:四角统一 `border_radius=16`,纯卡片风
5. **风格:Soft Twilight 暮光**(靛紫主 + 琥珀强调)
6. **封面:主色渐变 + 代表性 emoji**
7. **导航项:聊天/剧本/存档/设置**(4 个)
8. **数据完全向后兼容**:profiles/ JSON 格式不变
9. **core 层彻底解耦**:零 UI 框架依赖,未来换框架零成本
10. **emoji/图标问题已解决**:Flet 内置 Material/Cupertino 图标 + emoji 字体,无需手动注册

---

## 8. 给新 AI 的提示词模板

在新 opencode 会话(打开 `dorm-flet` 文件夹)中,可以用如下提示词启动:

> 这是一个 ChatRoom AI 角色扮演聊天应用的 Flet 重写项目。
> 环境搭建、数据迁移、core 业务层已全部完成并验证通过(见 `IMPLEMENTATION_GUIDE.md`)。
> 你的工作是纯 Flet UI 实现,从 `app/` 目录开始。
> 请先读 `IMPLEMENTATION_GUIDE.md` 了解完整规格,然后按其中的 Step 1-9 顺序实现。
> 从 Step 1(脚手架与主题)开始,每步完成后用 `flet run main.py` 验证。
