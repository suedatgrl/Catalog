import re
import secrets
import socket
import unicodedata
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
    """Arama için metni sadeleştirir: 'ÜTÜ' == 'ütü' == 'utu', 'Kâğıt' == 'kagit'.
    Hem ürün metni hem de müşterinin yazdığı kelime buradan geçtiği için
    Türkçe karakterle de, karaktersiz de yazılsa aynı sonuç bulunur."""
    text = str(text).translate(_TR_MAP)
    # â, î, û gibi şapkalı harfler ve bazı klavyelerin ayrık yazdığı işaretler (c + ¸)
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text.translate(_TR_MAP).lower()).strip()


def search_words(query):
    """Arama kelimeleri. Çoğul eki atılır: 'havlular' yazan 'havlu'yu da bulur."""
    words = []
    for word in normalize(query).split():
        if len(word) >= 6 and word.endswith(("ler", "lar")):
            word = word[:-3]
        words.append(word)
    return words


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


def lan_ip():
    """Bu bilgisayarın yerel ağdaki adresi (ör. 192.168.1.9). Bulunamazsa boş döner."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # paket gönderilmez; yalnızca çıkış arayüzü öğrenilir
            return s.getsockname()[0]
    except OSError:
        return ""


def site_url(request):
    """QR kodlara ve paylaşım bağlantılarına yazılacak kök adres."""
    if settings.SITE_URL:
        return settings.SITE_URL
    host = request.get_host()
    # Geliştirirken panel 127.0.0.1 üzerinden açılır ama telefon o adrese ulaşamaz;
    # QR kod telefonda da çalışsın diye bilgisayarın ağ adresini yazarız.
    name, _, port = host.partition(":")
    if settings.DEBUG and name in ("127.0.0.1", "localhost"):
        ip = lan_ip()
        if ip and not ip.startswith("127."):
            return f"http://{ip}:{port}" if port else f"http://{ip}"
    return f"{request.scheme}://{host}"
