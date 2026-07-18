# ChatRoom · AI 角色扮演聊天室

> 多人 AI 角色扮演聊天应用 — 创建一个故事世界，让 AI 角色们自由对话，你可以扮演其中一个，也可以充当「导演」掌控全局。

ChatRoom 的前身是 Kivy 桌面应用 [dorm-clean](https://github.com/bowenzhang01/Chatroom-Flet)，现已完全迁移至 **Flet** 框架，实现了：

- 🌐 **多平台支持** — Web / Windows / macOS / Linux / Android / iOS
- 🎨 **九色光谱主题** — 九种渐变色主题覆盖全光谱，浅色/深色随意切换
- ⚡ **流式输出** — LLM 逐 token 实时渲染，像打字一样流畅
- 🧠 **智能对话引擎** — 动态发言人选择、随机事件、路人 NPC、场景自动演化

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![Flet](https://img.shields.io/badge/Flet-0.24+-purple)

---

## 📸 预览

| 聊天视图 | 剧本管理 | 设置页面 |
|:---:|:---:|:---:|
| AI 角色实时对话 · 流式输出 · 场景切换 | 创建/编辑剧本 · AI 一键生成 | API 配置 · 主题切换 · 默认行为 |

## ✨ 核心功能

### 🤖 AI 角色扮演引擎

- **三种发言模式**：轮流 (`round`) / 随机 (`random`) / 动态 (`dynamic`，加权选人，含沉默惩罚、[NEXT] 提示响应)
- **导演模式** — 随时输入旁白/指令，注入到对话流中
- **用户模式** — 化身为 `You` 角色，以第一人称参与角色们的对话
- **动态场景** — AI 角色可以在回复中通过 `[SCENE]` 标签自动切换场景（时间/地点/氛围）

### 🎲 随机事件 & 路人 NPC

- 内置概率斜坡算法，对话中自动触发随机事件
- 路人 NPC 可被角色提及后回应，互动 2-3 轮或沉默后自行离开
- 参数内置默认值，开启即用

### ⚡ 流式输出

- 角色发言逐 token 实时渲染
- NPC 对话同样支持流式
- 在设置中可随时开关

### 🎨 九色光谱主题

| 主题 | 渐变色带 |
|:---|:---|
| 🟣 **极光** Aurora | 青→蓝→靛→紫 |
| 🌅 **暮光** Dusk | 粉→红→橙→琥珀→金黄 |
| 🌾 **金穗** Golden | 金黄→暖橙 |
| 🌿 **翠微** Jade | 青绿→翠绿→松绿 |
| 🌊 **海天** Ocean | 琥珀→青柠→翠→天蓝 |
| ☁️ **碧落** Sky | 天青→海蓝 |
| 💗 **赤霞** Crimson | 赤红→玫红 |
| 🌌 **星夜** Star | 蓝→靛→紫→粉 |
| 🌈 **虹光** Rainbow | 全光谱（红橙黄绿青蓝紫）|

每种主题含完整的浅色 / 深色配色方案。

### 📚 剧本管理

- 预设剧本：**女生寝室·日常** / **星际飞船**
- **AI 一键创建** — 输入一句话描述，多阶段并行生成：世界设定 → 场景 → 角色 → 用户化身
- 剧本详情：概览 / 场景 / 角色 / 发言顺序 / 随机事件开关
- AI 辅助：补全角色 / 推断世界观 / 生成场景 / 生成角色

### 💾 对话存档

- 自动存档 + 手动保存
- AI 自动生成对话标题
- 按日期分组浏览
- 启动时自动恢复未保存对话

---

## 🏗️ 项目架构

```
dorm-flet/
├── main.py                    # 入口脚本
├── config.py                  # 全局配置 & 路径常量
├── config.example.json        # 配置文件模板
├── utils.py                   # 纯工具函数（JSON、颜色等）
│
├── core/                      # 业务层（零 UI 框架依赖）
│   ├── app_state.py           # 应用全局状态中心
│   ├── ai_engine.py           # AI 引擎（prompt 构建 & LLM 调用）
│   ├── dialogue_loop.py       # 对话循环（后台线程）
│   ├── chat_manager.py        # 对话存档管理
│   ├── data_manager.py        # 剧本数据 CRUD
│   ├── events.py              # 事件总线 (EventBus)
│   └── debug.py               # 调试工具（DEBUG=dorm 启用）
│
├── services/                  # 服务层
│   ├── api_service.py         # LLM HTTP 封装（同步/异步/流式）
│   └── path_resolver.py       # 平台路径抽象（打包兼容）
│
├── app/                       # UI 层（Flet）
│   ├── main_app.py            # 应用入口组装
│   ├── theme.py               # 九色光谱主题
│   ├── router.py              # 响应式导航路由
│   ├── state.py               # UI 反应式状态
│   ├── views/                 # 视图
│   │   ├── chat_view.py       # 主聊天页
│   │   ├── profiles_view.py   # 剧本管理
│   │   ├── archives_view.py   # 对话存档
│   │   └── settings_view.py   # 设置
│   └── components/            # 可复用组件
│       ├── chat_bubble.py     # 消息气泡（流式渲染）
│       ├── transport_bar.py   # 播放控制栏
│       ├── mode_chips.py      # 模式选择 Chip 组
│       ├── director_input.py  # 导演/用户输入栏
│       ├── scene_banner.py    # 场景切换横幅
│       ├── progress_dialog.py # 进度弹窗
│       ├── profile_card.py    # 剧本封面卡
│       ├── character_card.py  # 角色卡片
│       └── reorderable_list.py # 拖拽排序列表
│
├── profiles/                  # 预设剧本数据
│   ├── dorm_life/             # 女生寝室·日常
│   └── starship/              # 星际飞船
│
├── assets/                    # 静态资源
│   └── NotoSansSC-Regular.ttf # 中文字体
│
└── build.ps1                  # Windows 构建脚本（本地）
```

### 设计原则

- **core 层与 UI 层彻底解耦** — 业务逻辑不含任何 Flet/Kivy 引用，未来换框架零成本
- **EventBus 驱动** — 后台线程通过事件总线通知 UI，替代轮询模型
- **线程安全** — Flet 的 `page.update()` 跨线程安全，无需主线程调度

### 数据流

```
用户操作 → UI 层 (app/)
              ↓ 调用
         core 层 (core/)
              ↓ 事件
         EventBus (core/events.py)
              ↓ 通知
         UI 层 更新控件
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- DeepSeek API Key（或兼容 OpenAI 接口的其他服务）

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制配置模板并填写：

```bash
cp config.example.json config.json
```

编辑 `config.json`：

```json
{
  "model": {
    "api_key": "sk-你的APIKey",
    "api_base": "https://api.deepseek.com",
    "model": "deepseek-v4-flash",
    "temperature": 0.85,
    "max_tokens": 500
  },
  "active_profile": "dorm_life"
}
```

> 💡 也可以通过环境变量 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY` 配置 Key（优先级高于 config.json）

### 3. 运行

**Web 模式（推荐调试）：**

```bash
flet run main.py --web --port 8080
```

**桌面模式：**

```bash
flet run main.py
```

### 调试模式

```bash
# Windows PowerShell
$env:DEBUG="dorm"; flet run main.py

# Linux/macOS
DEBUG=dorm flet run main.py
```

启用后会输出详细的线程检查、状态校验、EventBus 订阅追踪等信息。

---

## 📦 构建发布

Flet 支持一键构建多平台应用：

```bash
# Web
flet build web

# Windows 桌面
flet build windows

# macOS
flet build macos

# Android
flet build apk

# iOS
flet build ios
```

> ⚠️ 首次构建前，请执行 `flet build <platform> --help` 检查平台前置依赖。

---

## 🎮 使用指南

### 开始对话

1. 在设置页配置 API Key（或设置环境变量）
2. 切换到「聊天」页
3. 选择剧本和场景
4. 点击「▶ 开始对话」

### 模式说明

| 模式 | 开启/关闭 | 作用 |
|:---|:---|:---|
| **导演** | 随时切换 | 开启后在下方输入栏发送剧本指令 |
| **用户** | 随时切换 | 开启后你将以「你」的身份参与对话 |
| **动态场景** | 剧本设置中开启 | AI 角色可自动切换场景 |
| **随机事件** | 剧本设置中开启 | 对话中自动触发意外事件或路人 NPC |

### AI 一键创建剧本

1. 进入「剧本」页
2. 点击「✨ AI 创建」
3. 输入一句话描述（如「魔法学院的新生日常」）
4. AI 会依次完成：规划蓝图 → 生成场景 → 生成角色 → 组装完成
5. 弹窗中可看到每一步的实时进度

---

## 🛠️ 技术栈

| 层级 | 技术 |
|:---|:---|
| UI 框架 | [Flet](https://flet.dev) (Flutter in Python) |
| HTTP 客户端 | [httpx](https://www.python-httpx.org) |
| AI 接口 | DeepSeek API (OpenAI 兼容) |
| 字体 | Noto Sans SC |
| 打包 | Flet build / PyInstaller |

---

## 📝 开发历史

本项目从 Kivy 桌面应用 `dorm-clean` 迁移而来，经历了以下里程碑：

- **Kivy 版** — 原始的桌面聊天应用
- **Flet 迁移** — 完全重写 UI，core 层零依赖迁移
- **流式输出** — 添加 SSE 流式渲染支持
- **九色主题** — 从单一 Indigo 主题扩展为九色光谱
- **多平台基础** — 添加 Web/移动端编译配置
- **AI 生成重构** — 剧本生成从单次调用改为多阶段并行+进度追踪

---

## 📄 许可证

MIT License

---

*Built with ❤️ and AI*
