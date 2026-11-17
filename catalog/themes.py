"""Mağaza temaları. Esnaf serbest renk seçmek yerine birbiriyle uyumlu hazır
paletlerden birini seçer; böylece her mağaza derli toplu görünür.

Her tema müşteri sayfasındaki CSS değişkenlerini belirler:
  bg: sayfa zemini      surface: kart zemini     ink: yazı        muted: ikincil yazı
  line: ince çizgiler   accent: vurgu rengi      on: vurgu üstündeki yazı
  soft: vurgunun açık tonu (rozet, kutu zemini)  deep: karşılama alanındaki geçişin koyu ucu
"""

THEMES = {
    "kum": {
        "name": "Kum & Kiremit", "scheme": "light",
        "bg": "#f8f4ee", "surface": "#ffffff", "ink": "#221c18", "muted": "#7b7068",
        "line": "#ebe3d8", "accent": "#b4532a", "on": "#ffffff", "soft": "#f4e4d8", "deep": "#853717",
    },
    "orman": {
        "name": "Orman", "scheme": "light",
        "bg": "#f3f5ef", "surface": "#ffffff", "ink": "#18221c", "muted": "#68736b",
        "line": "#e1e7dc", "accent": "#2f5d4e", "on": "#ffffff", "soft": "#dde9df", "deep": "#1b3d33",
    },
    "okyanus": {
        "name": "Okyanus", "scheme": "light",
        "bg": "#f2f5fa", "surface": "#ffffff", "ink": "#101a2c", "muted": "#657089",
        "line": "#dfe5ef", "accent": "#2748c7", "on": "#ffffff", "soft": "#dee6fb", "deep": "#152a82",
    },
    "lavanta": {
        "name": "Lavanta", "scheme": "light",
        "bg": "#f6f4fb", "surface": "#ffffff", "ink": "#1d1830", "muted": "#6f6987",
        "line": "#e6e1f2", "accent": "#6a48c2", "on": "#ffffff", "soft": "#e8e0fa", "deep": "#432a8c",
    },
    "gul": {
        "name": "Gül Kurusu", "scheme": "light",
        "bg": "#fbf4f3", "surface": "#ffffff", "ink": "#2a1719", "muted": "#86696c",
        "line": "#f0dfdd", "accent": "#b23a57", "on": "#ffffff", "soft": "#f9e0e5", "deep": "#7c203a",
    },
    "komur": {
        "name": "Siyah & Beyaz", "scheme": "light",
        "bg": "#f5f5f3", "surface": "#ffffff", "ink": "#121212", "muted": "#6b6b6b",
        "line": "#e4e4e1", "accent": "#161616", "on": "#ffffff", "soft": "#e9e9e6", "deep": "#3d3d3d",
    },
    "gece": {
        "name": "Gece & Altın", "scheme": "dark",
        "bg": "#0e1116", "surface": "#171b22", "ink": "#f3efe8", "muted": "#9aa2ad",
        "line": "#272d37", "accent": "#e3b75f", "on": "#1b1405", "soft": "#2a2416", "deep": "#b98a2e",
    },
}

DEFAULT_THEME = "kum"
THEME_CHOICES = [(key, t["name"]) for key, t in THEMES.items()]
_CSS_KEYS = ["bg", "surface", "ink", "muted", "line", "accent", "on", "soft", "deep"]


def get_theme(key):
    return THEMES.get(key) or THEMES[DEFAULT_THEME]


def css_vars(key):
    """<body style="..."> içine yazılacak değişkenler."""
    theme = get_theme(key)
    parts = [f"--{k}: {theme[k]}" for k in _CSS_KEYS]
    parts.append(f"color-scheme: {theme['scheme']}")
    return "; ".join(parts)
