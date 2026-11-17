import re
import secrets
import uuid
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.text import slugify
from PIL import Image, ImageOps

_TR_MAP = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iIsSgGuUoOcC")
_CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # karışan harfler (l/1, o/0) yok


def tr_slugify(text):
    """Türkçe karakterleri kaybetmeden slug üretir: 'Çift Kişilik' -> 'cift-kisilik'."""
    return slugify(str(text).translate(_TR_MAP))


def normalize(text):
    """Arama için: Türkçe harfleri sadeleştirip küçültür ('ÜTÜ' == 'utu')."""
    return re.sub(r"\s+", " ", str(text).translate(_TR_MAP).lower()).strip()


def make_code(length=7):
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


def unique_slug(queryset, text, fallback="urun", max_length=80):
    base = tr_slugify(text)[: max_length - 6] or fallback
    slug, n = base, 2
    while queryset.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def process_image(upload, max_side, quality=82, keep_alpha=False):
    """Yüklenen görseli döndürür/küçültür ve WebP'ye çevirir (mobilde hızlı açılsın)."""
    upload.seek(0)
    img = Image.open(upload)
    img = ImageOps.exif_transpose(img)
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    if has_alpha and keep_alpha:
        img = img.convert("RGBA")
    elif has_alpha:
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, "WEBP", quality=quality, method=4)
    return ContentFile(buf.getvalue(), name=f"{uuid.uuid4().hex}.webp")


def whatsapp_number(raw):
    """'0532 111 22 33' -> '905321112233' (wa.me biçimi)."""
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = "90" + digits[1:]
    elif len(digits) == 10 and digits.startswith("5"):
        digits = "90" + digits
    return digits


def site_url(request):
    return settings.SITE_URL or f"{request.scheme}://{request.get_host()}"


def text_on(hex_color):
    """Verilen zemin renginin üstünde okunaklı yazı rengi."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return "#111827" if (0.299 * r + 0.587 * g + 0.114 * b) > 165 else "#ffffff"
