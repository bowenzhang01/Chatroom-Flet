# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 四色光谱主题 (Spectrum Themes)
  四种渐变色主题，在设置中随时切换：
    虹光 Rainbow — 全光谱青绿→青→蓝→靛→紫→粉→琥珀→红
    暮光 Dusk    — 紫红→橙黄 (粉→红→橙→琥珀→金)
    海天 Ocean   — 橙黄→蓝绿 (琥珀→青柠→翠→青→天蓝)
    星夜 Star    — 蓝紫→紫红 (蓝→靛→紫→粉)
  同时保留浅色/深色切换（每主题两套配色）。
"""

import flet as ft

__all__ = [
    "build_theme",
    "rebuild_themes",
    "set_color_theme",
    "get_color_theme_key",
    "THEME_MODES",
    "THEME_NAMES",
    "COLORS",
    "GRADIENT_BAND",
    "profile_gradient",
    "char_color_at",
    "profile_emoji",
    "RADIUS_CARD",
    "RADIUS_BUBBLE",
    "RADIUS_PILL",
    "SPACING",
]

# ═══ 当前选中主题（模块级，任意地方 import 即可拿到当前 gradient band）═══
_current_color_theme_key = "aurora"


def set_color_theme(key: str):
    global _current_color_theme_key
    if key in COLOR_THEMES:
        _current_color_theme_key = key


def get_color_theme_key() -> str:
    return _current_color_theme_key


# ═══ 主题模式映射（浅色 / 深色 / 系统）═══
THEME_MODES = {
    "light": ft.ThemeMode.LIGHT,
    "dark": ft.ThemeMode.DARK,
    "system": ft.ThemeMode.SYSTEM,
}


# ═══ 圆角 / 间距令牌 ═══
RADIUS_CARD = 16
RADIUS_BUBBLE = 16
RADIUS_PILL = 999

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "xxl": 32,
}


# ═══════════════════════════════════════════════════════════════
#  四色光谱主题定义
# ═══════════════════════════════════════════════════════════════

COLOR_THEMES: dict[str, dict] = {}

# ── 主题 1：极光 Aurora · 青蓝→紫（原默认主题）──
COLOR_THEMES["aurora"] = {
    "name": "极光",
    "seed_light": ft.Colors.BLUE,
    "seed_dark": ft.Colors.INDIGO,
    "gradient_band": [
        "#22D3EE",  # cyan
        "#3B82F6",  # blue
        "#6366F1",  # indigo
        "#8B5CF6",  # violet
    ],
    "light": {
        "surface": "#F7F9FF",
        "primary": "#4F6FF7",
        "on_primary": "#FFFFFF",
        "primary_container": "#E0E7FF",
        "on_primary_container": "#1A1F2E",
        "bubble_ai": "#EEF1FE",
        "bubble_ai_text": "#1A1F2E",
        "director": "#FEF3C7",
        "director_text": "#3D3520",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#1A1F2E",
        "text_secondary": "#5B6273",
        "text_hint": "#8B92A5",
        "outline": "#C9D0E6",
        "surface_container_low": "#F0F3FC",
        "surface_container_high": "#E7EBF8",
    },
    "dark": {
        "surface": "#0F1420",
        "primary": "#818CF8",
        "on_primary": "#0F1420",
        "primary_container": "#2A2F4A",
        "on_primary_container": "#E6E7F0",
        "bubble_ai": "#1A1F2E",
        "bubble_ai_text": "#E6E7F0",
        "director": "#3D3520",
        "director_text": "#FCE7B0",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#E6E7F0",
        "text_secondary": "#A0A7BD",
        "text_hint": "#6B7290",
        "outline": "#2A3148",
        "surface_container_low": "#1A1F2E",
        "surface_container_high": "#222840",
    },
}

# ── 主题 2：暮光 Dusk · 紫红→橙黄 ──
COLOR_THEMES["dusk"] = {
    "name": "暮光",
    "seed_light": ft.Colors.DEEP_ORANGE,
    "seed_dark": ft.Colors.ORANGE,
    "gradient_band": [
        "#EC4899",  # pink
        "#EF4444",  # red
        "#F97316",  # orange
        "#F59E0B",  # amber
        "#FBBF24",  # yellow
    ],
    "light": {
        "surface": "#FFF5F0",
        "primary": "#F97316",
        "on_primary": "#FFFFFF",
        "primary_container": "#FFEDD5",
        "on_primary_container": "#2D1600",
        "bubble_ai": "#FFF0EB",
        "bubble_ai_text": "#2D1600",
        "director": "#FFFBEB",
        "director_text": "#3D3020",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#EF4444",
        "text": "#1A1015",
        "text_secondary": "#706060",
        "text_hint": "#A09090",
        "outline": "#E0D0C8",
        "surface_container_low": "#FFF0EB",
        "surface_container_high": "#FFE8E0",
    },
    "dark": {
        "surface": "#1A1015",
        "primary": "#F97316",
        "on_primary": "#1A1015",
        "primary_container": "#3D2A20",
        "on_primary_container": "#FED7AA",
        "bubble_ai": "#1F1618",
        "bubble_ai_text": "#E8D5D0",
        "director": "#3D3020",
        "director_text": "#FCE7B0",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#E8D5D0",
        "text_secondary": "#B0A0A0",
        "text_hint": "#807070",
        "outline": "#3D2A30",
        "surface_container_low": "#1F1618",
        "surface_container_high": "#2A1E22",
    },
}

# ── 主题 3：海天 Ocean · 橙黄→蓝绿 ──
COLOR_THEMES["ocean"] = {
    "name": "海天",
    "seed_light": ft.Colors.TEAL,
    "seed_dark": ft.Colors.CYAN,
    "gradient_band": [
        "#F59E0B",  # amber
        "#84CC16",  # lime
        "#10B981",  # emerald
        "#14B8A6",  # teal
        "#06B6D4",  # cyan
    ],
    "light": {
        "surface": "#F0FBFA",
        "primary": "#14B8A6",
        "on_primary": "#FFFFFF",
        "primary_container": "#CCFBF1",
        "on_primary_container": "#042F2E",
        "bubble_ai": "#EEF9F8",
        "bubble_ai_text": "#042F2E",
        "director": "#FEF3C7",
        "director_text": "#3D3520",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#042F2E",
        "text_secondary": "#5B706E",
        "text_hint": "#8BA09E",
        "outline": "#C8DEDB",
        "surface_container_low": "#EEF9F8",
        "surface_container_high": "#E2F5F3",
    },
    "dark": {
        "surface": "#0F1F1E",
        "primary": "#2DD4BF",
        "on_primary": "#0F1F1E",
        "primary_container": "#1A3A38",
        "on_primary_container": "#CCFBF1",
        "bubble_ai": "#142220",
        "bubble_ai_text": "#D0E8E5",
        "director": "#3D3520",
        "director_text": "#FCE7B0",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#D0E8E5",
        "text_secondary": "#90B0AD",
        "text_hint": "#60807E",
        "outline": "#2A403E",
        "surface_container_low": "#142220",
        "surface_container_high": "#1E302E",
    },
}

# ── 主题 4：星夜 Star · 蓝紫→紫红 ──
COLOR_THEMES["star"] = {
    "name": "星夜",
    "seed_light": ft.Colors.DEEP_PURPLE,
    "seed_dark": ft.Colors.INDIGO,
    "gradient_band": [
        "#3B82F6",  # blue
        "#6366F1",  # indigo
        "#8B5CF6",  # violet
        "#A855F7",  # purple
        "#EC4899",  # pink
    ],
    "light": {
        "surface": "#F7F5FF",
        "primary": "#7C3AED",
        "on_primary": "#FFFFFF",
        "primary_container": "#EDE9FE",
        "on_primary_container": "#1E0040",
        "bubble_ai": "#F2EFFE",
        "bubble_ai_text": "#1E0040",
        "director": "#FEF3C7",
        "director_text": "#3D3520",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#1A1025",
        "text_secondary": "#6B6280",
        "text_hint": "#9B92A5",
        "outline": "#D5CFE6",
        "surface_container_low": "#F2EFFE",
        "surface_container_high": "#E8E3F8",
    },
    "dark": {
        "surface": "#100F1F",
        "primary": "#A78BFA",
        "on_primary": "#100F1F",
        "primary_container": "#2E204A",
        "on_primary_container": "#E4DDFC",
        "bubble_ai": "#18162A",
        "bubble_ai_text": "#E0D8F0",
        "director": "#3D3520",
        "director_text": "#FCE7B0",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#E0D8F0",
        "text_secondary": "#A098C0",
        "text_hint": "#7068A0",
        "outline": "#30284A",
        "surface_container_low": "#18162A",
        "surface_container_high": "#221E38",
    },
}

# 映射中文名 → key
THEME_NAMES = {v["name"]: k for k, v in COLOR_THEMES.items()}

# ── 向后兼容：COLORS 始终指向当前主题 ──
def _current_colors():
    return COLOR_THEMES[_current_color_theme_key]

# 动态属性：COLORS["light"] / COLORS["dark"] 跟随当前主题
class _ColorsProxy:
    def __getitem__(self, key):
        ct = COLOR_THEMES.get(_current_color_theme_key, COLOR_THEMES["aurora"])
        return ct[key]
    def get(self, key, default=None):
        ct = COLOR_THEMES.get(_current_color_theme_key, COLOR_THEMES["aurora"])
        return ct.get(key, default)
    def __iter__(self):
        ct = COLOR_THEMES.get(_current_color_theme_key, COLOR_THEMES["aurora"])
        return iter(ct)

COLORS = _ColorsProxy()

# ═══ 渐变带（跟随当前主题）═══
def _current_gradient_band():
    ct = COLOR_THEMES.get(_current_color_theme_key, COLOR_THEMES["aurora"])
    return ct["gradient_band"]

# 向后兼容：模块级 GRADIENT_BAND 跟随当前主题
class _GradientBandProxy:
    def __iter__(self):
        return iter(_current_gradient_band())
    def __getitem__(self, idx):
        return _current_gradient_band()[idx]
    def __len__(self):
        return len(_current_gradient_band())
    def __repr__(self):
        return repr(_current_gradient_band())

GRADIENT_BAND = _GradientBandProxy()


# ═══ 颜色插值工具 ═══

def _hex_to_rgb(hex_str: str) -> tuple:
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: tuple) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _lerp(a, b, t):
    return a + (b - a) * t


def _color_at(t: float, band=None) -> str:
    """渐变带上 t∈[0,1] 处的颜色（线性插值）。未传 band 则用当前主题渐变带。"""
    t = max(0.0, min(1.0, t))
    b = band if band is not None else _current_gradient_band()
    n = len(b) - 1
    pos = t * n
    i = int(pos)
    f = pos - i
    if i >= n:
        return b[n]
    c1 = _hex_to_rgb(b[i])
    c2 = _hex_to_rgb(b[i + 1])
    return _rgb_to_hex(tuple(round(_lerp(c1[k], c2[k], f)) for k in range(3)))


# 角色头像只取冷色调子集
_CHAR_COLOR_START = 0.10
_CHAR_COLOR_END = 0.70


# ═══ 主题 → (关键词组, emoji, 渐变起点t, 渐变跨度) ═══
_THEME_DEFS = [
    (("寝室","宿舍","日常","校园","生活","学校","学生","dorm","life","室友","同桌"), "🏠",   0.00, 0.35),
    (("魔法","奇幻","巫师","咒语","妖精","精灵","魔","magic","fantasy","witch","fairy"), "🪄",   0.20, 0.50),
    (("星","飞船","太空","科幻","宇宙","星际","银河","外星","star","ship","space","alien","planet"), "🚀",   0.45, 0.55),
    (("武","江湖","侠","功夫","门派","剑","sword","kungfu","martial"), "⚔️",   0.00, 0.25),
    (("恐怖","惊悚","黑暗","吸血鬼","怪物","鬼","horror","zombie","dark","haunt","cursed"), "🕯️",   0.60, 0.40),
    (("末日","废土","幸存","丧尸","wasteland","apocalypse","survival"), "🏚️",   0.75, 0.25),
    (("冒险","勇者","探险","西部","沙漠","遗迹","寻宝","adventure","quest","ruins","treasure"), "🗺️",   0.80, 0.20),
    (("恋爱","浪漫","甜","爱情","甜蜜","约会","romance","love","couple","date","heart"), "💕",   0.65, 0.30),
    (("古装","宫廷","古风","修仙","ancient","皇帝","皇朝","朝代","剑仙","仙侠","宫"), "🏮",   0.90, 0.10),
    (("都市","办公室","公司","职场","modern","office","city","白领","上班"), "🏙️",   0.25, 0.28),
    (("侦探","推理","mystery","案件","破案","crime","罪案","线索"), "🔍",   0.35, 0.20),
    (("田园","乡村","农场","旅行","自然","森林","山","海","nature","forest","farm","trip"), "🌿",   0.05, 0.20),
    (("历史","战争","革命","帝国","王朝","history","war","empire","dynasty","起义"), "📜",   0.88, 0.12),
    (("医院","医生","医疗","护士","急诊","病人","medical","clinic","patient","病房"), "🏥",   0.12, 0.20),
    (("音乐","乐队","歌","演奏","演唱会","乐器","music","band","rock","jazz","pop"), "🎵",   0.55, 0.30),
    (("运动","体育","篮球","足球","比赛","竞技","球","sports","match","race","game"), "⚽",   0.35, 0.40),
    (("美食","料理","餐厅","甜点","咖啡","烘焙","food","cook","bake","chef","kitchen"), "🍳",   0.82, 0.18),
    (("悬疑","惊悚","thriller","suspense","紧张","谜团"), "👁️",   0.42, 0.18),
    (("神话","传说","龙","神","myth","legend","dragon","god","deity"), "🐉",   0.75, 0.20),
    (("海盗","船","航海","海洋","pirate","sail","ocean","sea"), "⚓",   0.30, 0.35),
    (("蒸汽","机械","齿轮","steam","punk","gear","mecha","robot"), "⚙️",   0.50, 0.30),
]


def _match_theme(text: str):
    for keywords, emoji, start_t, span in _THEME_DEFS:
        if any(k in text for k in keywords):
            return emoji, start_t, span
    return None


def profile_gradient(seed: str, title: str = "") -> ft.LinearGradient:
    """剧本封面渐变：根据关键词从全色渐变带上取一个区段。"""
    text = (seed + title)
    matched = _match_theme(text)
    if matched:
        _, start_t, span = matched
    else:
        s = (abs(hash(seed)) % 100) / 100.0 if seed else 0.3
        start_t, span = s * 0.65, 0.35
    end_t = min(1.0, start_t + span)
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_LEFT,
        end=ft.Alignment.BOTTOM_RIGHT,
        colors=[_color_at(start_t), _color_at(end_t)],
    )


def char_color_at(index: int, total: int) -> str:
    """角色头像 hue：沿冷色调子集均匀分配。"""
    if total <= 1:
        return _color_at(0.50)
    t = index / (total - 1)
    return _color_at(_CHAR_COLOR_START + t * (_CHAR_COLOR_END - _CHAR_COLOR_START))


# ═══ 剧本封面 emoji ═══

def profile_emoji(folder_name: str, title: str = "") -> str:
    text = (folder_name + title)
    matched = _match_theme(text)
    if matched:
        return matched[0]
    return "📖"


_PILL_SHAPE = ft.StadiumBorder()
_CARD_SHAPE = ft.RoundedRectangleBorder(radius=RADIUS_CARD)


# ═══ 主题构建 ═══

def build_theme(theme_key: str = "aurora", mode: str = "light") -> ft.Theme:
    """构建 Flet Theme。

    theme_key: 'aurora' | 'dusk' | 'ocean' | 'star'
    mode: 'light' | 'dark'
    """
    ct = COLOR_THEMES.get(theme_key, COLOR_THEMES["aurora"])
    is_dark = mode == "dark"
    c = ct[mode]
    seed = ct["seed_dark" if is_dark else "seed_light"]

    cs = ft.ColorScheme(
        primary=c["primary"],
        on_primary=c["on_primary"],
        primary_container=c["primary_container"],
        on_primary_container=c["on_primary_container"],
        surface=c["surface"],
        surface_container_low=c["surface_container_low"],
        surface_container_high=c["surface_container_high"],
        outline=c["outline"],
        on_surface=c["text"],
        on_surface_variant=c["text_secondary"],
        secondary=c["director_accent"],
        tertiary=c["success"],
        error=c["danger"],
    )

    theme = ft.Theme(
        color_scheme=cs,
        color_scheme_seed=seed,
        font_family="Noto Sans SC",
        use_material3=True,
        canvas_color=c["surface"],
        scaffold_bgcolor=c["surface"],
    )

    theme.card_theme = ft.CardTheme(shape=_CARD_SHAPE)
    theme.chip_theme = ft.ChipTheme(shape=_PILL_SHAPE)
    _pill_style = ft.ButtonStyle(shape=_PILL_SHAPE)
    theme.filled_button_theme = ft.FilledButtonTheme(style=_pill_style)
    theme.outlined_button_theme = ft.OutlinedButtonTheme(style=_pill_style)
    theme.text_button_theme = ft.TextButtonTheme(style=_pill_style)
    theme.button_theme = ft.ButtonTheme(style=_pill_style)
    theme.floating_action_button_theme = ft.FloatingActionButtonTheme(shape=_PILL_SHAPE)

    return theme


def rebuild_themes(page: ft.Page, theme_key: str):
    """切换色彩主题时调用：重建 page.theme 和 page.dark_theme。"""
    page.theme = build_theme(theme_key, "light")
    page.dark_theme = build_theme(theme_key, "dark")
