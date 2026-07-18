[English](./README.md) | [中文](./README_CN.md)

# ChatRoom · AI Multi-Character Role-Play Chatroom

> A multi-character AI role-playing chat app — create a story world, let AI characters talk freely. Jump in as one of them, or orchestrate everything as the "Director".

ChatRoom is a complete rewrite of the original Kivy desktop app [ChatRoom](https://github.com/bowenzhang01/ChatRoom), now built on **Flet** (see [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) for migration details):

- 🌐 **Cross-Platform** — Web / Windows / macOS / Linux / Android / iOS
- 🎨 **9 Color Themes** — Gradient themes spanning the full color spectrum, with light/dark modes
- ⚡ **Streaming Output** — LLM responses render token-by-token in real time
- 🧠 **Smart Dialogue Engine** — Dynamic speaker selection, random events, NPC passers-by, automatic scene evolution

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![Flet](https://img.shields.io/badge/Flet-0.24+-purple)

---

## ✨ Features

### 🤖 AI Role-Play Engine

- **Three speaking modes**:
  - `round` — Fixed turn order
  - `random` — Random speaker each turn
  - `dynamic` — Smart weighted selection with silence penalty, direct mention boost (×3), [NEXT] hint response (×5), and anti-monologue (×0.1)
- **Director Mode** — Inject stage directions at any time; characters respond naturally to your orchestration
- **User Mode** — Embody a character (`You`) and interact with AI characters as an equal
- **Dynamic Scenes** — AI characters can switch scenes via `[SCENE]` tags, evolving time/location/mood as the conversation progresses
- **Adjustable Speed** — 1–10 speed slider to control the pacing between character turns

### 🎲 Random Events & NPCs

The world doesn't just sit still while characters talk:

- **Random Events**: Built-in probability ramp algorithm (3-turn cooldown + probability climbing to 35%), automatically triggering environmental changes (storms, blackouts, knocks on the door…)
- **Passer-by NPCs**: Randomly generated temporary characters with names, backstories, and distinct personalities
- **NPC Interaction**: Characters mention NPC → NPC responds for 2–3 turns and leaves naturally; 4 turns without being mentioned → quietly fades away
- **Streaming NPCs**: NPC dialogue also supports streaming output
- All parameters use sensible defaults; toggle on/off in profile settings with one click

### ⚡ Streaming Output

- Character dialogue renders token-by-token into chat bubbles via SSE (Server-Sent Events)
- NPC dialogue follows the same streaming pipeline
- Toggle streaming on/off anytime in settings

### 📚 AI One-Click Profile Creation

Describe your story in one sentence. AI generates a complete profile in four parallel phases:

| Phase | Content | Method |
|:---|:---|:---|
| **Planning** | World setting + title + scene/character hints | 1 API call |
| **Scenes** | 4 complete scenes (time/location/mood/description) | 4 parallel API calls |
| **Characters** | 4–5 complete characters (personality/tone/appearance/system prompt) | 4–5 parallel API calls |
| **Assembly** | User avatar + title optimization | 2 parallel API calls |

Real-time progress shown in dialog (e.g. `✓ Scenes 3/4 · ⏳ Characters 2/5`).

Also supports:
- **AI Complete Character** — Fill in missing fields for existing characters with one click
- **AI Infer World** — Reverse-engineer world setting from title and scenes
- **AI Generate Scenes** — Expand new scenes based on existing characters and world
- **AI Generate Characters** — Generate new characters based on scenes and world

### 🗣️ Turn Order & Modes

- **Drag-to-reorder**: Freely adjust speaking order via drag-and-drop
- **Standby characters**: Drag characters between "active" and "standby"
- **Dynamic Scene toggle**: Allow AI characters to carry `[SCENE]` tags to auto-advance the scene
- **Random Event toggle**: Independent control, doesn't affect other modes

### 💾 Chat Archives

- **Auto-save**: Automatically saves on pause and window close — never lose a message
- **Startup recovery**: Prompts to restore unsaved conversations on launch
- **AI title generation**: Automatically generates titles from conversation content (e.g. "Late Night Dorm Talk")
- **Grouped by date**: Today / Yesterday / Earlier — clear at a glance
- **Archive management**: Load, delete, rename

### 🎨 Theme System

Nine gradient color themes spanning the full spectrum from crimson to violet. Each includes complete light/dark color schemes. Switch anytime in settings:

| Aurora · Cyan→Violet | Dusk · Pink→Gold | Golden · Gold→Orange | Jade · Green | Ocean · Amber→Cyan |
|:---:|:---:|:---:|:---:|:---:|
| Sky · Sky Blue | Crimson · Red→Rose | Star · Blue→Purple | Rainbow · Full Spectrum | — |

### 🔒 Security

- **Environment variable priority**: `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` env vars > `config.json` — prevents key leakage to Git
- **config.json gitignored**: Repository only contains `config.example.json` (no keys); actual config never uploaded
- **Auto-init on first launch**: `config.json` auto-copies from `config.example.json` if missing
- Custom API base URL supported; compatible with any OpenAI-compatible service

---

## 🏗️ Architecture

```
dorm-flet/
├── main.py                    # Entry point
├── config.py                  # Global config & path constants
├── utils.py                   # Pure utilities (JSON, color, stream parsing)
│
├── core/                      # Business layer (zero UI dependency)
│   ├── app_state.py           # Centralized app state
│   ├── ai_engine.py           # AI engine (prompt building, LLM calls, tag parsing)
│   ├── dialogue_loop.py       # Main dialogue loop (background thread + streaming pipeline)
│   ├── chat_manager.py        # Archive management (read/write/auto-save/recovery)
│   ├── data_manager.py        # Profile CRUD (characters, scenes, config)
│   ├── events.py              # EventBus
│   └── debug.py               # Debug tools (enable with DEBUG=dorm)
│
├── services/                  # Service layer
│   ├── api_service.py         # LLM HTTP (sync/async/SSE streaming)
│   └── path_resolver.py       # Platform paths (dev/packaged/mobile)
│
├── app/                       # UI layer (Flet)
│   ├── main_app.py            # App assembly entry
│   ├── theme.py               # 9-spectrum theme (gradients, color tokens)
│   ├── router.py              # Responsive navigation (desktop Rail / mobile NavBar)
│   ├── state.py               # UI reactive state
│   ├── views/                 # Four main views
│   │   ├── chat_view.py       # Chat (bubbles, streaming, scroll-to-bottom)
│   │   ├── profiles_view.py   # Profile management (card grid, details, drag)
│   │   ├── archives_view.py   # Chat archives
│   │   └── settings_view.py   # Settings (API, appearance, behavior, about)
│   └── components/            # Reusable components
│
├── profiles/                  # Built-in profiles
│   ├── dorm_life/             # Girls' Dorm Daily (5 chars + 4 scenes)
│   └── starship/              # Starship (5 chars + 5 scenes)
│
└── assets/                    # Fonts & static assets
```

### Design Highlights

- **Core ↔ UI fully decoupled**: Business layer contains zero Flet/Kivy references — swap UI frameworks at zero cost
- **EventBus-driven**: Background threads emit events → UI handlers update controls, no polling
- **Thread-safe**: Flet's `page.update()` is cross-thread safe; event callbacks update UI directly
- **Streaming pipeline**: `msg → msg_delta(multiple) → msg_end`, sharing rendering logic with non-streaming mode

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Notes |
|:---|:---|
| Python 3.10+ (3.12 recommended) | Best cross-platform compatibility |
| DeepSeek API Key | [Sign up here](https://platform.deepseek.com) |
| (Optional) Git | For cloning the repository |

> ⚠️ Flet requires Python ≥ 3.10. This project is not fully tested on 3.14+. **Python 3.12 recommended.**

### 1. Clone & Enter

```bash
git clone https://github.com/bowenzhang01/Chatroom-Flet.git
cd Chatroom-Flet
```

### 2. Create a Virtual Environment

Not strictly required, but highly recommended:

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Only two core dependencies:

| Package | Version | Purpose |
|:---|:---|:---|
| `flet` | ≥ 0.24.0 | UI framework, installs `flet` CLI tool |
| `httpx` | ≥ 0.28.0 | HTTP client for LLM API calls (including SSE streaming) |

### 4. Configure API Key

On first launch, the app auto-copies `config.example.json` to `config.json` (includes complete defaults: model list, theme, behavior toggles, etc.). **You only need to provide an API Key.**

Three options:

**🌍 Option A: Environment Variable (safest, recommended)**

```bash
# Windows PowerShell
$env:DEEPSEEK_API_KEY = "sk-your-key"

# Linux / macOS / WSL
export DEEPSEEK_API_KEY="sk-your-key"
```

Set this and launch — no file modifications needed. The key only lives in the current terminal session.

**📄 Option B: Edit config.json**

Open the auto-generated `config.json` and fill in `api_key`:

```json
{
  "model": {
    "api_key": "sk-your-key",
    "api_base": "https://api.deepseek.com",
    "model": "deepseek-v4-flash"
  }
}
```

> `config.json` is gitignored and will never be uploaded. If accidentally deleted, restart the app to regenerate from `config.example.json`.

**🔌 Option C: Use Another API Provider**

Any OpenAI-compatible chat/completions API works. Change `api_base` and `api_key`:

```json
{
  "model": {
    "api_key": "your-key",
    "api_base": "https://api.openai.com/v1",
    "model": "gpt-4o-mini"
  }
}
```

Also supports Ollama local models (`http://localhost:11434/v1`), together.ai, Groq, and other providers.

### 5. Launch

```bash
# Web mode — opens http://localhost:8080 in browser
flet run main.py --web --port 8080

# Desktop mode — native window
flet run main.py
```

Once the UI appears: go to ⚙️ Settings → click "Test Connection" to verify the API → back to 💬 Chat → click ▶ Start → characters begin talking!

### 6. Debug Mode

Enable for troubleshooting (outputs thread checks, state validation, EventBus subscription traces):

```bash
# Windows PowerShell
$env:DEBUG="dorm"; flet run main.py --web

# Linux / macOS
DEBUG=dorm flet run main.py --web
```

---

## 📦 Build & Deploy

Flet compiles Python projects into standalone applications:

| Platform | Command | Output |
|:---|:---|:---|
| 🌐 Web | `flet build web` | `build/web/` static files |
| 🪟 Windows | `flet build windows` | `build/windows/` folder |
| 🍎 macOS | `flet build macos` | `.app` bundle |
| 📱 Android | `flet build apk` | `.apk` |
| 📱 iOS | `flet build ios` | `.ipa` (requires macOS + Xcode) |

### 🌐 Web — Simplest Deployment

```bash
flet build web
```

Generates `build/web/` — deploy to any static hosting:

```bash
# Local preview
cd build/web && python -m http.server 8080

# Deploy to GitHub Pages / Vercel / Netlify / Cloudflare Pages
```

No runtime required. Works in any browser.

### 🪟 Windows Desktop

**Prerequisites:**

1. **Visual Studio 2022 Build Tools** — [Download](https://visualstudio.microsoft.com/downloads/), select "Desktop development with C++" workload
2. **Enable Developer Mode** (one-time only):
   ```powershell
   # Run as Administrator in PowerShell
   reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" /v AllowDevelopmentWithoutDevLicense /t REG_DWORD /d 1 /f
   ```

**Build:**

```bash
# First build downloads Flutter SDK (~1GB), cached thereafter
flet build windows --product "ChatRoom"
```

Output is in `build/windows/`. Zip the entire folder to distribute.

**Customization:**

```bash
flet build windows \
  --product "ChatRoom" \
  --description "AI Multi-Character Role-Play Chatroom" \
  --icon assets/icon.png
```

Common `flet build` flags:
- `--product` — Application name (window title bar)
- `--description` — Application description
- `--icon` — App icon (256×256 PNG recommended)
- `--python-version` — Target Python version (e.g. `3.12`), defaults to system version

### 🍎 macOS

```bash
# Install prerequisites
xcode-select --install

# Build
flet build macos
```

### 📱 Android

```bash
flet build apk
```

Prerequisites:
- Install [Android Studio](https://developer.android.com/studio)
- SDK Manager → install Android SDK Platform 34+
- Set `ANDROID_HOME` environment variable (typically `%LOCALAPPDATA%\Android\Sdk`)
- JDK 17+

### 📱 iOS

```bash
flet build ios
```

Prerequisites: macOS + Xcode 15+. Physical device deployment requires an Apple Developer account.

### ⚙️ Custom App Name & Icon

```bash
flet build web \
  --product "ChatRoom" \
  --description "AI Multi-Character Role-Play Chatroom" \
  --icon assets/icon.png
```

See `flet build --help` for more options.

---

## 🎮 Usage Guide

### Getting Started

1. **Set API Key** → Go to Settings, fill in API base URL and key, test connection
2. **Choose a profile** → Built-in "Girls' Dorm Daily" and "Starship" profiles
3. **Start** → Click ▶, characters begin autonomous dialogue
4. **Intervene** → Enable Director mode to send stage directions, or User mode to join as a character
5. **Save** → Conversations auto-save; also manual save available

### AI Profile Creation

Go to Profiles → click "✨ AI Create" → enter a description (e.g. "A cyberpunk bar at midnight") → wait for multi-phase generation to complete → start your new story.

---

## 🛠️ Tech Stack

| Layer | Technology | Notes |
|:---|:---|:---|
| UI | [Flet](https://flet.dev) | Flutter in Python |
| Network | [httpx](https://www.python-httpx.org) | HTTP + SSE streaming |
| AI | DeepSeek API | OpenAI-compatible |
| Font | Noto Sans SC | CJK rendering |
| Packaging | Flet build | Multi-platform one-click build |

---

## 📝 Migration History

This project is a complete rewrite of the Kivy-based [ChatRoom](https://github.com/bowenzhang01/ChatRoom). Technical migration details and UI design specs in [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md).

Key milestones:
- **Kivy → Flet full migration** — UI layer completely rewritten, core layer preserved with zero dependencies
- **EventBus replaces Queue+Clock polling** — Cleaner event-driven architecture
- **Streaming output** — SSE token-by-token rendering, toggleable mid-session
- **AI generation refactored** — Single API call → multi-phase parallel + progress tracking
- **9-color themes** — Single Indigo → full spectrum coverage

---

## 📄 License

MIT License
