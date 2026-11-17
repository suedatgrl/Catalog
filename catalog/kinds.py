"""
Özel dikim ürün türleri. Her tür; çizim şeklini, müşteriden istenecek ölçüleri,
renk seçilebilecek parçaları ve hazır ölçü önerilerini belirler.
Yeni bir tür eklemek için buraya bir kayıt, static/js/visualizer.js içine de
(gerekirse) yeni bir çizim şekli eklemek yeterli.

dims: (anahtar, etiket, en az, en çok, varsayılan)  — hepsi cm
"""

BED_PRESETS = [
    ("Tek kişilik", {"w": 90, "l": 190}),
    ("Tek (geniş)", {"w": 100, "l": 200}),
    ("Çift kişilik", {"w": 160, "l": 200}),
    ("King", {"w": 180, "l": 200}),
    ("Bebek", {"w": 70, "l": 130}),
]
BED_DIMS = [
    ("w", "Yatak eni", 50, 240, 160),
    ("l", "Yatak boyu", 100, 240, 200),
    ("h", "Yatak yüksekliği", 5, 50, 25),
]

KINDS = {
    "nevresim": {
        "label": "Nevresim takımı",
        "shape": "bed",
        "dims": BED_DIMS,
        "parts": [("duvet", "Nevresim"), ("sheet", "Çarşaf"), ("pillow", "Yastık kılıfı")],
        "presets": BED_PRESETS,
    },
    "carsaf": {
        "label": "Lastikli çarşaf",
        "shape": "bed",
        "dims": BED_DIMS,
        "parts": [("sheet", "Çarşaf"), ("pillow", "Yastık kılıfı")],
        "presets": BED_PRESETS,
    },
    "yatak_ortusu": {
        "label": "Yatak örtüsü",
        "shape": "bed",
        "dims": BED_DIMS,
        "parts": [("cover", "Örtü"), ("pillow", "Yastık kılıfı")],
        "presets": BED_PRESETS,
    },
    "koltuk": {
        "label": "Koltuk örtüsü / kılıfı",
        "shape": "sofa",
        "dims": [
            ("w", "Koltuk genişliği", 60, 340, 210),
            ("h", "Sırt yüksekliği", 60, 120, 85),
            ("d", "Oturma derinliği", 40, 120, 60),
        ],
        "parts": [("body", "Gövde"), ("cushion", "Minderler")],
        "presets": [
            ("Tekli", {"w": 95}),
            ("İkili", {"w": 155}),
            ("Üçlü", {"w": 210}),
            ("Dörtlü", {"w": 270}),
        ],
    },
    "perde": {
        "label": "Perde",
        "shape": "curtain",
        "dims": [
            ("w", "Korniş genişliği", 50, 600, 240),
            ("h", "Perde boyu", 50, 320, 260),
        ],
        "parts": [("curtain", "Kumaş")],
        "presets": [
            ("Pencere", {"w": 150, "h": 160}),
            ("Balkon kapısı", {"w": 240, "h": 260}),
            ("Salon", {"w": 400, "h": 260}),
        ],
    },
    "masa": {
        "label": "Masa örtüsü",
        "shape": "table",
        "dims": [
            ("w", "Masa eni", 40, 200, 90),
            ("l", "Masa boyu", 40, 400, 160),
            ("s", "Sarkma payı", 0, 60, 25),
        ],
        "parts": [("cloth", "Örtü")],
        "presets": [
            ("4 kişilik", {"w": 80, "l": 120}),
            ("6 kişilik", {"w": 90, "l": 160}),
            ("8 kişilik", {"w": 100, "l": 220}),
            ("Kare", {"w": 90, "l": 90}),
        ],
    },
    "minder": {
        "label": "Minder / sedir",
        "shape": "cushion",
        "dims": [
            ("w", "En", 20, 300, 120),
            ("l", "Boy", 20, 200, 60),
            ("h", "Kalınlık", 2, 40, 10),
        ],
        "parts": [("main", "Kumaş"), ("piping", "Biye")],
        "presets": [
            ("Sandalye", {"w": 40, "l": 40, "h": 5}),
            ("Balkon", {"w": 120, "l": 50, "h": 8}),
            ("Sedir", {"w": 190, "l": 70, "h": 12}),
        ],
    },
}

KIND_CHOICES = [(key, k["label"]) for key, k in KINDS.items()]


def kind_config(key):
    """Bir türün ayarlarını JSON'a uygun biçimde döndürür."""
    k = KINDS[key]
    return {
        "kind": key,
        "shape": k["shape"],
        "dims": [
            {"key": d[0], "label": d[1], "min": d[2], "max": d[3], "def": d[4]} for d in k["dims"]
        ],
        "parts": [{"key": p[0], "label": p[1]} for p in k["parts"]],
        "presets": [{"label": p[0], "values": p[1]} for p in k["presets"]],
    }
