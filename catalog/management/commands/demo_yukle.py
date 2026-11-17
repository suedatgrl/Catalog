"""Deneme için örnek bir mağaza kurar:  python manage.py demo_yukle
Yalnızca geliştirme/tanıtım içindir; üretimde çalıştırmayın."""
import math
import random
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageDraw, ImageFilter

from catalog.models import Category, CustomItem, FabricColor, Product, ProductImage, Shop, ShopMember
from catalog.utils import process_image

PRODUCTS = [
    # kategori, ad, fiyat, eski fiyat, bedenler, renkler, özellikler, açıklama, öne çıkan
    ("Nevresim", "Ranforce Çift Kişilik Nevresim Takımı", 1299, 1599, "Çift kişilik, King", "Lacivert, Gri, Pudra", "Kumaş: %100 pamuk ranforce\nİçerik: Nevresim, çarşaf, 2 yastık kılıfı", "Yumuşak dokulu, terletmeyen pamuklu nevresim takımı.", True),
    ("Nevresim", "Saten Tek Kişilik Nevresim Takımı", 949, None, "Tek kişilik", "Beyaz, Bej", "Kumaş: Pamuk saten", "", False),
    ("Nevresim", "Lastikli Penye Çarşaf", 389, 449, "90x190, 160x200, 180x200", "Beyaz, Gri, Mint", "", "Her mevsim kullanılabilen esnek penye çarşaf.", False),
    ("Havlu & Bornoz", "Pamuklu Banyo Havlusu 70x140", 279, None, "", "Beyaz, Antrasit, Hardal", "Gramaj: 500 gr/m²", "", False),
    ("Havlu & Bornoz", "Kapüşonlu Bornoz", 899, 1099, "S/M, L/XL", "Beyaz, Lacivert", "", "Kalın dokulu, su emiciliği yüksek bornoz.", True),
    ("Havlu & Bornoz", "Çocuk Bornozu", 459, None, "4-5, 6-7, 8-9, 10-11 yaş", "Sarı, Mavi", "", "", False),
    ("Havlu & Bornoz", "El ve Yüz Havlusu 2'li Set", 249, 299, "", "Beyaz, Gri", "Gramaj: 450 gr/m²", "", False),
    ("Ev Tekstili", "Kapitone Yatak Örtüsü", 1890, None, "Çift kişilik", "Ekru, Gri", "", "Çift taraflı kullanılabilir.", False),
    ("Küçük Ev Aletleri", "Buharlı Ütü 2400 W", 1749, 1999, "", "", "Güç: 2400 W\nTaban: Seramik\nSu haznesi: 300 ml\nGaranti: 2 yıl", "Güçlü şok buhar, damlatmaz taban.", True),
    ("Küçük Ev Aletleri", "Cam Su Isıtıcı 1,7 L", 899, None, "", "", "Güç: 2200 W\nHacim: 1,7 L\nGaranti: 2 yıl", "", False),
    ("Küçük Ev Aletleri", "El Blender Seti", 1299, 1499, "", "", "Güç: 1000 W\nParça: Çırpıcı, doğrayıcı, ölçü kabı\nGaranti: 2 yıl", "", False),
    ("Küçük Ev Aletleri", "Tost Makinesi", None, None, "", "", "Güç: 1800 W\nGaranti: 2 yıl", "Granit plakalı, 4 dilim kapasiteli.", False),
    ("Küçük Ev Aletleri", "Dikey Şarjlı Süpürge", 4999, 5799, "", "", "Çalışma süresi: 45 dk\nGaranti: 2 yıl", "", False),
]

COLORS = [
    ("Kırık beyaz", "#f5f1e8", "duz", "#ffffff"),
    ("Lacivert", "#1e3a5f", "duz", "#ffffff"),
    ("Antrasit", "#44474c", "duz", "#ffffff"),
    ("Pudra", "#e8c4c0", "duz", "#ffffff"),
    ("Adaçayı", "#9caf88", "duz", "#ffffff"),
    ("Hardal", "#d4a017", "duz", "#ffffff"),
    ("Kiremit", "#b5533c", "duz", "#ffffff"),
    ("Lacivert çizgili", "#f5f1e8", "cizgili", "#1e3a5f"),
    ("Gri ekose", "#f3f4f6", "kareli", "#6b7280"),
    ("Puantiyeli pudra", "#e8c4c0", "puantiye", "#ffffff"),
]

CUSTOM = [
    ("nevresim", "Nevresim takımı", "Pamuk ranforce; nevresim, çarşaf ve yastık kılıfı.", 350, 180),
    ("carsaf", "Lastikli çarşaf", "Yatağınızın tam ölçüsüne göre.", 100, 160),
    ("yatak_ortusu", "Yatak örtüsü", "Kapitone, çift taraflı.", 400, 260),
    ("koltuk", "Koltuk örtüsü", "Yıkanabilir, kaymaz tabanlı.", 500, 220),
    ("perde", "Fon perde", "Pileli dikim, astarlı.", 300, 240),
    ("masa", "Masa örtüsü", "Leke tutmaz kumaş.", 80, 200),
    ("minder", "Minder / sedir", "Fermuarlı kılıf, sünger dahil değil.", 150, 230),
]


# Sakin, doğal tonlar: (koyu, açık)
TONES = [
    ("#b9a58d", "#efe6d7"), ("#8fa08a", "#e3e9da"), ("#9fb2bf", "#e6edf1"), ("#d3a9a0", "#f6e6e1"),
    ("#7f776d", "#e6e0d7"), ("#b58f6e", "#f0e2d0"), ("#6f8190", "#dde4e8"), ("#c9a47e", "#f3e6d4"),
]
SIZES = [(800, 1000), (800, 1200), (800, 800), (800, 1066), (800, 1000), (800, 1280)]


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def placeholder(index, appliance=False):
    """Gerçek fotoğraf yerine stüdyo çekimi hissi veren örnek görsel üretir:
    kumaş kıvrımları (tekstil) ya da nötr fonda bir nesne (küçük ev aletleri).
    Boyutlar çeşitlidir; böylece fotoğraf akışı (masonry) gerçekçi görünür."""
    rnd = random.Random(index * 7919)
    dark, light = (_hex(c) for c in TONES[index % len(TONES)])
    w, h = SIZES[index % len(SIZES)]
    sw, sh = w // 2, h // 2  # yarı çözünürlükte çiz, sonra büyüt (yumuşak görünür, hızlı üretilir)

    if appliance:
        img = Image.new("RGB", (sw, sh))
        px = img.load()
        horizon = int(sh * 0.68)
        for y in range(sh):
            t = y / sh
            base = _lerp(light, tuple(min(255, v + 18) for v in light), t) if y < horizon else _lerp(
                tuple(max(0, v - 14) for v in light), tuple(max(0, v - 34) for v in light), (y - horizon) / (sh - horizon))
            for x in range(sw):
                px[x, y] = base
        layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        bw, bh = int(sw * rnd.uniform(.38, .5)), int(sh * rnd.uniform(.3, .4))
        x0, y1 = (sw - bw) // 2, horizon + int(sh * .06)
        shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse([x0 - 10, y1 - 14, x0 + bw + 10, y1 + 16], fill=(40, 30, 20, 90))
        img.paste(shadow.filter(ImageFilter.GaussianBlur(9)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(9)))
        body = tuple(max(0, v - 70) for v in dark)
        d.rounded_rectangle([x0, y1 - bh, x0 + bw, y1], radius=int(bw * .18), fill=body + (255,))
        d.rounded_rectangle([x0 + 8, y1 - bh + 8, x0 + bw // 3, y1 - 10], radius=int(bw * .1), fill=(255, 255, 255, 46))
        hx = x0 + bw if rnd.random() < .5 else x0 - int(bw * .16)
        d.rounded_rectangle([hx, y1 - int(bh * .72), hx + int(bw * .16), y1 - int(bh * .3)], radius=10, fill=body + (255,))
        img.paste(layer, (0, 0), layer)
    else:
        # Çapraz kumaş kıvrımları: iki dalganın toplamı + kenarlarda hafif kararma
        ang = rnd.uniform(-.7, .7)
        ca, sa = math.cos(ang), math.sin(ang)
        f1, f2 = rnd.uniform(.016, .026), rnd.uniform(.05, .08)
        ph1, ph2 = rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)
        img = Image.new("RGB", (sw, sh))
        px = img.load()
        for y in range(sh):
            for x in range(sw):
                u = x * ca + y * sa
                t = .5 + .34 * math.sin(u * f1 + ph1 + .8 * math.sin(y * .011)) + .16 * math.sin(u * f2 + ph2)
                px[x, y] = _lerp(dark, light, max(0, min(1, t)))

    img = img.resize((w, h), Image.LANCZOS)
    # İnce dokuma/film greni ve hafif vinyet
    grain = Image.effect_noise((w, h), 26).convert("RGB")
    img = Image.blend(img, grain, 0.05)
    mask = Image.radial_gradient("L").resize((w, h))
    shade = Image.new("RGB", (w, h), tuple(max(0, v - 60) for v in dark))
    img = Image.composite(img, shade, mask.point(lambda v: min(255, 150 + v)))
    buf = BytesIO()
    img.save(buf, "JPEG", quality=88)
    return ContentFile(buf.getvalue(), name="demo.jpg")


class Command(BaseCommand):
    help = "Örnek bir mağaza, ürünler, renk kartelası ve panel kullanıcısı oluşturur."

    def add_arguments(self, parser):
        parser.add_argument("--slug", default="ornek-vitrin", help="Mağaza adresi")
        parser.add_argument("--ad", default="Atölye Ev & Tekstil", help="Mağaza adı")
        parser.add_argument("--tema", default="kum", help="Tema anahtarı (kum, orman, okyanus, lavanta, gul, komur, gece)")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("demo_yukle bilinen bir şifreyle kullanıcı oluşturur; yalnızca DEBUG açıkken çalışır.")
        slug = options["slug"]
        if Shop.objects.filter(slug=slug).exists():
            self.stdout.write(f"Bu adreste mağaza zaten var: /{slug}/")
            return

        shop = Shop.objects.create(
            name=options["ad"],
            slug=slug,
            tagline="Ev tekstili ve küçük ev aletleri",
            description="1998'den beri mahallenizin ev tekstili ve ev gereçleri dükkânı. Ölçüye özel dikim yapılır.",
            phone="0212 555 00 00",
            whatsapp="0532 555 00 00",
            instagram="ornektekstil",
            address="Çarşı Cad. No: 12, Kadıköy / İstanbul",
            working_hours="Pzt–Cmt 09:00–20:00",
            theme=options["tema"],
        )
        user, created = get_user_model().objects.get_or_create(username="demo")
        if created:
            user.set_password("demo12345")
            user.save()
        ShopMember.objects.get_or_create(shop=shop, user=user)

        cats = {}
        for i, row in enumerate(PRODUCTS):
            cat_name, name, price, old, sizes, colors, specs, desc, featured = row
            if cat_name not in cats:
                cats[cat_name] = Category.objects.create(shop=shop, name=cat_name, order=len(cats))
            product = Product.objects.create(
                shop=shop, category=cats[cat_name], name=name, price=price, old_price=old,
                sizes=sizes, colors=colors, specs=specs, description=desc, is_featured=featured,
                in_stock=(i != 7),
            )
            for n in range(2 if featured else 1):
                src = placeholder(i * 3 + n, appliance=cat_name == "Küçük Ev Aletleri")
                ProductImage.objects.create(
                    product=product, image=process_image(src, 1600),
                    thumb=process_image(src, 600, quality=78), order=n,
                )

        for i, (name, hex_, pattern, hex2) in enumerate(COLORS):
            FabricColor.objects.create(shop=shop, name=name, hex=hex_, pattern=pattern, hex2=hex2, order=i)
        for i, (kind, name, desc, base, m2) in enumerate(CUSTOM):
            CustomItem.objects.create(
                shop=shop, kind=kind, name=name, description=desc, base_price=base, price_per_m2=m2, order=i
            )

        self.stdout.write(self.style.SUCCESS(
            "Örnek mağaza hazır.\n"
            f"  Mağaza : /{slug}/\n"
            "  Panel  : /panel/   (kullanıcı: demo  şifre: demo12345)"
        ))
