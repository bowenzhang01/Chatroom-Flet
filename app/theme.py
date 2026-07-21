# -*- coding: utf-8 -*-
"""
ChatRoom - Flet Edition · 光谱主题 (Spectrum Themes)
   九种渐变色主题覆盖完整光谱，在设置中随时切换：
      赤霞 Crimson — 赤红→玫红 (红→玫瑰→粉)
      暮光 Dusk    — 粉红→金黄 (粉→红→橙→琥珀→金黄)
      金穗 Golden  — 金黄→暖橙 (金→琥珀→蜜橙)
      翠微 Jade    — 青绿→翠绿 (青柠→绿→翠→松绿)
      海天 Ocean   — 琥珀→天青 (琥珀→青柠→翠→青→天蓝)
      碧落 Sky     — 天青→海蓝 (浅天蓝→天蓝→深天蓝→海蓝)
      极光 Aurora  — 青蓝→紫 (青→蓝→靛→紫)
      星夜 Star    — 蓝紫→玫粉 (蓝→靛→紫→粉)
      虹光 Rainbow — 全光谱 (红→橙→黄→绿→青→蓝→紫)
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
    "TEXT_EMOJI",
    "TEXT_XXL",
    "TEXT_XL",
    "TEXT_LG",
    "TEXT_ML",
    "TEXT_MD",
    "TEXT_SM",
    "TEXT_XS",
]

# ═══ 文字尺寸常量 ═══
# Flet 0.86.0 不支持 textScaleFactor，无法阻止 Android 系统字体缩放。
# 此处尺寸已较设计值缩小 ~20%，使系统 1.3× 缩放后实际尺寸接近原始设计值。
# 1.0× 系统缩放下：文字比设计值略小但仍清晰可读。
# 1.3× 系统缩放下：实际尺寸 ≈ 原始设计值，布局不会被撑破。
#
# 映射关系（设计值 → 常量）：
#   56 → TEXT_EMOJI (44)   大 emoji（空状态封面）
#   22 → TEXT_XXL  (18)    超大标题（空状态标题）
#   20 → TEXT_XL   (16)    页面标题（存档/剧本库/设置）
#   18 → TEXT_LG   (14)    对话标题（chat header）
#   16 → TEXT_ML   (13)    avatar 文字、角色卡名
#   15 → TEXT_ML   (13)    卡片标题、分区标题
#   14 → TEXT_MD   (11)    正文（角色名、气泡、卡片标题）
#   13 → TEXT_SM   (10)    辅助文字（场景、状态、segment）
#   12 → TEXT_SM   (10)    辅助文字（标签、元信息）
#   11 → TEXT_XS   (9)     极小（时间戳、提示、描述）
#   10 → TEXT_XS   (9)     极小（徽章、时间戳）

TEXT_EMOJI = 44
TEXT_XXL = 18
TEXT_XL = 16
TEXT_LG = 14
TEXT_ML = 13
TEXT_MD = 11
TEXT_SM = 10
TEXT_XS = 9

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
#  九色光谱主题定义
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

# ── 主题 5：赤霞 Crimson · 赤红→玫红 ──
COLOR_THEMES["crimson"] = {
    "name": "赤霞",
    "seed_light": ft.Colors.RED,
    "seed_dark": ft.Colors.PINK,
    "gradient_band": [
        "#DC2626",  # red
        "#E11D48",  # rose
        "#EC4899",  # pink
        "#BE185D",  # deep pink
    ],
    "light": {
        "surface": "#FFF5F5",
        "primary": "#E11D48",
        "on_primary": "#FFFFFF",
        "primary_container": "#FFE4E6",
        "on_primary_container": "#2D0008",
        "bubble_ai": "#FFF0F0",
        "bubble_ai_text": "#2D0008",
        "director": "#FEF3C7",
        "director_text": "#3D3520",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#DC2626",
        "text": "#1A0A10",
        "text_secondary": "#705860",
        "text_hint": "#A09098",
        "outline": "#E0D0D5",
        "surface_container_low": "#FFF0F0",
        "surface_container_high": "#FFE8E8",
    },
    "dark": {
        "surface": "#1A0A10",
        "primary": "#F43F5E",
        "on_primary": "#1A0A10",
        "primary_container": "#3D1A25",
        "on_primary_container": "#FECDD3",
        "bubble_ai": "#1F1216",
        "bubble_ai_text": "#E8D0D5",
        "director": "#3D3520",
        "director_text": "#FCE7B0",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#E8D0D5",
        "text_secondary": "#B098A0",
        "text_hint": "#806870",
        "outline": "#3D2530",
        "surface_container_low": "#1F1216",
        "surface_container_high": "#2A1A22",
    },
}

# ── 主题 6：金穗 Golden · 金黄→暖橙 ──
COLOR_THEMES["golden"] = {
    "name": "金穗",
    "seed_light": ft.Colors.AMBER,
    "seed_dark": ft.Colors.YELLOW,
    "gradient_band": [
        "#FBBF24",  # yellow
        "#F59E0B",  # amber
        "#EA580C",  # orange
        "#C2410C",  # deep orange
    ],
    "light": {
        "surface": "#FFFDF0",
        "primary": "#EAB308",
        "on_primary": "#FFFFFF",
        "primary_container": "#FEF9C3",
        "on_primary_container": "#2D2000",
        "bubble_ai": "#FFFBEB",
        "bubble_ai_text": "#2D2000",
        "director": "#FEF3C7",
        "director_text": "#3D3520",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#1A1500",
        "text_secondary": "#706830",
        "text_hint": "#A09860",
        "outline": "#E0D8B8",
        "surface_container_low": "#FFFBEB",
        "surface_container_high": "#FFF8E0",
    },
    "dark": {
        "surface": "#1A1410",
        "primary": "#FBBF24",
        "on_primary": "#1A1410",
        "primary_container": "#3D3020",
        "on_primary_container": "#FEF9C3",
        "bubble_ai": "#1F1A14",
        "bubble_ai_text": "#E8E0C0",
        "director": "#3D3520",
        "director_text": "#FCE7B0",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#E8E0C0",
        "text_secondary": "#B0A878",
        "text_hint": "#807848",
        "outline": "#3D3828",
        "surface_container_low": "#1F1A14",
        "surface_container_high": "#2A2418",
    },
}

# ── 主题 7：翠微 Jade · 青绿→翠绿 ──
COLOR_THEMES["jade"] = {
    "name": "翠微",
    "seed_light": ft.Colors.GREEN,
    "seed_dark": ft.Colors.LIGHT_GREEN,
    "gradient_band": [
        "#84CC16",  # lime
        "#22C55E",  # green
        "#16A34A",  # forest
        "#15803D",  # deep green
        "#166534",  # pine
    ],
    "light": {
        "surface": "#F0FDF4",
        "primary": "#16A34A",
        "on_primary": "#FFFFFF",
        "primary_container": "#DCFCE7",
        "on_primary_container": "#002A10",
        "bubble_ai": "#EEF9F2",
        "bubble_ai_text": "#002A10",
        "director": "#FEF3C7",
        "director_text": "#3D3520",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#001A08",
        "text_secondary": "#5B7060",
        "text_hint": "#8BA090",
        "outline": "#C8DED0",
        "surface_container_low": "#EEF9F2",
        "surface_container_high": "#E2F5E8",
    },
    "dark": {
        "surface": "#0F1A14",
        "primary": "#4ADE80",
        "on_primary": "#0F1A14",
        "primary_container": "#1A3525",
        "on_primary_container": "#DCFCE7",
        "bubble_ai": "#142018",
        "bubble_ai_text": "#D0E8D5",
        "director": "#3D3520",
        "director_text": "#FCE7B0",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#D0E8D5",
        "text_secondary": "#90B098",
        "text_hint": "#608068",
        "outline": "#2A4030",
        "surface_container_low": "#142018",
        "surface_container_high": "#1E3028",
    },
}

# ── 主题 8：碧落 Sky · 天青→海蓝 ──
COLOR_THEMES["sky"] = {
    "name": "碧落",
    "seed_light": ft.Colors.CYAN,
    "seed_dark": ft.Colors.BLUE,
    "gradient_band": [
        "#38BDF8",  # light sky
        "#0EA5E9",  # sky blue
        "#0284C7",  # deep sky
        "#0369A1",  # ocean blue
    ],
    "light": {
        "surface": "#F0F8FF",
        "primary": "#0EA5E9",
        "on_primary": "#FFFFFF",
        "primary_container": "#E0F2FE",
        "on_primary_container": "#002840",
        "bubble_ai": "#EEF4FE",
        "bubble_ai_text": "#002840",
        "director": "#FEF3C7",
        "director_text": "#3D3520",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#001528",
        "text_secondary": "#5B6A78",
        "text_hint": "#8B9AA5",
        "outline": "#C8D5E0",
        "surface_container_low": "#EEF4FE",
        "surface_container_high": "#E2ECF8",
    },
    "dark": {
        "surface": "#0F1820",
        "primary": "#38BDF8",
        "on_primary": "#0F1820",
        "primary_container": "#1A2D3D",
        "on_primary_container": "#E0F2FE",
        "bubble_ai": "#141C24",
        "bubble_ai_text": "#D0DEE8",
        "director": "#3D3520",
        "director_text": "#FCE7B0",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#D0DEE8",
        "text_secondary": "#90A5B5",
        "text_hint": "#607585",
        "outline": "#2A3845",
        "surface_container_low": "#141C24",
        "surface_container_high": "#1E2832",
    },
}

# ── 主题 9：虹光 Rainbow · 全光谱 ──
COLOR_THEMES["rainbow"] = {
    "name": "虹光",
    "seed_light": ft.Colors.PINK,
    "seed_dark": ft.Colors.DEEP_PURPLE,
    "gradient_band": [
        "#EF4444",  # red
        "#F97316",  # orange
        "#FBBF24",  # yellow
        "#22C55E",  # green
        "#06B6D4",  # cyan
        "#3B82F6",  # blue
        "#8B5CF6",  # violet
    ],
    "light": {
        "surface": "#F8FAFB",
        "primary": "#6366F1",
        "on_primary": "#FFFFFF",
        "primary_container": "#EEF0FF",
        "on_primary_container": "#1A1A2E",
        "bubble_ai": "#F4F5FA",
        "bubble_ai_text": "#1A1A2E",
        "director": "#FEF3C7",
        "director_text": "#3D3520",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#1A1A2E",
        "text_secondary": "#6B6B80",
        "text_hint": "#9B9BA5",
        "outline": "#D0D0E0",
        "surface_container_low": "#F4F5FA",
        "surface_container_high": "#E8EAF2",
    },
    "dark": {
        "surface": "#12121A",
        "primary": "#A78BFA",
        "on_primary": "#12121A",
        "primary_container": "#2A2A40",
        "on_primary_container": "#E0DDFC",
        "bubble_ai": "#1A1A24",
        "bubble_ai_text": "#E0E0F0",
        "director": "#3D3520",
        "director_text": "#FCE7B0",
        "director_accent": "#F59E0B",
        "success": "#10B981",
        "danger": "#F43F5E",
        "text": "#E0E0F0",
        "text_secondary": "#A0A0C0",
        "text_hint": "#707090",
        "outline": "#303045",
        "surface_container_low": "#1A1A24",
        "surface_container_high": "#242430",
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

    theme_key: 'crimson' | 'dusk' | 'golden' | 'jade' | 'ocean' | 'sky' | 'aurora' | 'star' | 'rainbow'
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
