"""Deneme için örnek bir mağaza kurar:  python manage.py demo_yukle
Yalnızca geliştirme/tanıtım içindir; üretimde çalıştırmayın."""
import colorsys
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
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


def placeholder(index):
    """Gerçek fotoğraf yerine yumuşak renk geçişli bir örnek görsel üretir."""
    hue = (index * 0.137) % 1
    top = tuple(int(v * 255) for v in colorsys.hls_to_rgb(hue, .86, .45))
    bottom = tuple(int(v * 255) for v in colorsys.hls_to_rgb((hue + .06) % 1, .70, .50))
    w, h = 800, 1000
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        draw.line([(0, y), (w, y)], fill=tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)))
    shape = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shape)
    sd.rounded_rectangle([170, 300, 630, 760], radius=70, fill=(255, 255, 255, 110))
    sd.ellipse([300, 180, 500, 380], fill=(255, 255, 255, 80))
    img.paste(shape.filter(ImageFilter.GaussianBlur(2)), (0, 0), shape)
    buf = BytesIO()
    img.save(buf, "JPEG", quality=85)
    return ContentFile(buf.getvalue(), name="demo.jpg")


class Command(BaseCommand):
    help = "Örnek bir mağaza, ürünler, renk kartelası ve panel kullanıcısı oluşturur."

    def handle(self, *args, **options):
        if Shop.objects.filter(slug="ornek-magaza").exists():
            self.stdout.write("Örnek mağaza zaten var: /ornek-magaza/")
            return

        shop = Shop.objects.create(
            name="Örnek Tekstil & Ev",
            slug="ornek-magaza",
            tagline="Ev tekstili ve küçük ev aletleri",
            description="1998'den beri mahallenizin ev tekstili ve ev gereçleri dükkânı. Ölçüye özel dikim yapılır.",
            phone="0212 555 00 00",
            whatsapp="0532 555 00 00",
            instagram="ornektekstil",
            address="Çarşı Cad. No: 12, Kadıköy / İstanbul",
            working_hours="Pzt–Cmt 09:00–20:00",
            theme="kum",
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
                src = placeholder(i * 3 + n)
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
            "  Mağaza : /ornek-magaza/\n"
            "  Panel  : /panel/   (kullanıcı: demo  şifre: demo12345)"
        ))
