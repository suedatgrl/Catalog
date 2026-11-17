"""Mağaza temaları. Esnaf serbest renk seçmek yerine birbiriyle uyumlu hazır
paletlerden birini seçer; böylece her mağaza derli toplu görünür.

Her tema müşteri sayfasındaki CSS değişkenlerini belirler:
  bg: sayfa zemini      surface: kart/alan zemini   ink: yazı        muted: ikincil yazı
  line: ince çizgiler   accent: vurgu rengi         on: vurgu üstündeki yazı
  soft: yumuşak zemin (alt bilgi, kutular)          deep: vurgunun koyu tonu

Paletler "doğal ve sakin" tutuldu (kum, zeytin, sis, pudra…): ürün fotoğrafları öne çıksın.
Yazı renkleri zeminde en az ~5:1 kontrast verir.
"""

THEMES = {
    "kum": {
        "name": "Kum", "scheme": "light",
        "bg": "#faf8f3", "surface": "#fffdf9", "ink": "#2a2420", "muted": "#6d6258",
        "line": "#ede5d8", "accent": "#9a5a3a", "on": "#fffaf4", "soft": "#f0e9dd", "deep": "#6b3b22",
    },
    "orman": {
        "name": "Zeytin", "scheme": "light",
        "bg": "#f8f8f4", "surface": "#fbfbf6", "ink": "#232820", "muted": "#666c5b",
        "line": "#e5e6da", "accent": "#59683f", "on": "#fbfbf6", "soft": "#eaeddd", "deep": "#39461f",
    },
    "okyanus": {
        "name": "Sis", "scheme": "light",
        "bg": "#f6f8f9", "surface": "#fafcfc", "ink": "#1d272c", "muted": "#5f6e76",
        "line": "#e0e6e9", "accent": "#456a7c", "on": "#fafcfc", "soft": "#e4edf1", "deep": "#2b4857",
    },
    "lavanta": {
        "name": "Lavanta", "scheme": "light",
        "bg": "#f9f8fb", "surface": "#fcfbfe", "ink": "#241f2e", "muted": "#6a6277",
        "line": "#e9e5f1", "accent": "#67508f", "on": "#fcfbfe", "soft": "#eee8f6", "deep": "#40305f",
    },
    "gul": {
        "name": "Pudra", "scheme": "light",
        "bg": "#fcf6f4", "surface": "#fffaf8", "ink": "#2d2020", "muted": "#7a5f61",
        "line": "#f1e3e0", "accent": "#a85a62", "on": "#fffaf8", "soft": "#f6e4e2", "deep": "#733a41",
    },
    "komur": {
        "name": "Mermer", "scheme": "light",
        "bg": "#f9f9f8", "surface": "#ffffff", "ink": "#161616", "muted": "#666663",
        "line": "#e9e9e6", "accent": "#1c1c1c", "on": "#ffffff", "soft": "#eeeeeb", "deep": "#3b3b39",
    },
    "gece": {
        "name": "Gece & Altın", "scheme": "dark",
        "bg": "#14120f", "surface": "#1d1a16", "ink": "#f2ebe0", "muted": "#a99f90",
        "line": "#2e2923", "accent": "#d9b36c", "on": "#1b1405", "soft": "#2a2419", "deep": "#9c7a3a",
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
