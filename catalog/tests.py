import json
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Category, CustomItem, CustomRequest, FabricColor, Product, Shop, ShopMember
from .templatetags.catalog_extras import tl
from .utils import normalize, tr_slugify, whatsapp_number

MEDIA = tempfile.mkdtemp()


def png(name="foto.png"):
    buf = BytesIO()
    Image.new("RGB", (2000, 1200), "#3366aa").save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA)
class Base(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()  # hız sınırı sayaçları testler arasında sızmasın
        User = get_user_model()
        self.shop = Shop.objects.create(name="Ayşe Tekstil", slug="ayse", whatsapp="0532 111 22 33")
        self.other = Shop.objects.create(name="Öteki Dükkân", slug="oteki")
        self.user = User.objects.create_user("ayse", password="gizli-sifre-1")
        ShopMember.objects.create(shop=self.shop, user=self.user)
        self.cat = Category.objects.create(shop=self.shop, name="Küçük Ev Aletleri")
        self.product = Product.objects.create(
            shop=self.shop, category=self.cat, name="Buharlı Ütü", price=1500, old_price=2000
        )
        self.foreign = Product.objects.create(shop=self.other, name="Yabancı Ürün", price=10)


class HelperTests(TestCase):
    def test_turkish_helpers(self):
        self.assertEqual(tr_slugify("Çift Kişilik Işıltı"), "cift-kisilik-isilti")
        self.assertEqual(normalize("ÜTÜ  Masası"), "utu masasi")
        self.assertEqual(whatsapp_number("0532 111 22 33"), "905321112233")
        self.assertEqual(whatsapp_number("+90 532 111 22 33"), "905321112233")
        self.assertEqual(tl(1299), "1.299 ₺")
        self.assertEqual(tl("1299.9"), "1.299,90 ₺")


class SiteUrlTests(TestCase):
    @override_settings(DEBUG=True, SITE_URL="")
    def test_localhost_uses_lan_address_with_same_port(self):
        from unittest import mock

        from .utils import site_url

        request = mock.Mock(scheme="http")
        request.get_host.return_value = "127.0.0.1:8000"
        with mock.patch("catalog.utils.lan_ip", return_value="192.168.1.9"):
            self.assertEqual(site_url(request), "http://192.168.1.9:8000")
        request.get_host.return_value = "magaza.example.com"
        self.assertEqual(site_url(request), "http://magaza.example.com")
        with override_settings(SITE_URL="https://ornek.com"):
            self.assertEqual(site_url(request), "https://ornek.com")


class StoreTests(Base):
    def test_shop_page_and_search(self):
        r = self.client.get("/ayse/")
        self.assertContains(r, "Buharlı Ütü")
        self.assertNotContains(r, "Yabancı Ürün")
        self.assertContains(r, "%25")
        self.assertContains(self.client.get("/ayse/?q=UTU"), "Buharlı Ütü")
        self.assertNotContains(self.client.get("/ayse/?q=tencere"), "Buharlı Ütü")
        self.assertContains(self.client.get(f"/ayse/?kategori={self.cat.slug}"), "Buharlı Ütü")

    def test_turkish_search(self):
        Product.objects.create(shop=self.shop, name="Çocuk Kâğıt Işıklı Şarjlı Süpürge", specs="Güç: 2400 W")
        hits = ["çocuk", "ÇOCUK", "cocuk", "ışıklı", "IŞIKLI", "isikli", "İşıklı", "şarjlı", "sarjli",
                "süpürge", "SÜPÜRGE", "supurge", "süpürgeler", "kağıt", "kâğıt", "kagit",
                "c\u0327ocuk", "şarjlı süpürge", "2400"]
        for q in hits:
            with self.subTest(q=q):
                self.assertContains(self.client.get("/ayse/", {"q": q}), "Şarjlı Süpürge")
        self.assertNotContains(self.client.get("/ayse/", {"q": "çorap"}), "Şarjlı Süpürge")
        # kategori adı değişince arama yeni adla da bulur
        self.cat.name = "Elektrikli Eşyalar"
        self.cat.save()
        self.assertContains(self.client.get("/ayse/", {"q": "eşya"}), "Buharlı Ütü")

    def test_hidden_product_and_shop(self):
        self.product.is_active = False
        self.product.save()
        self.assertNotContains(self.client.get("/ayse/"), "Buharlı Ütü")
        self.assertEqual(self.client.get(self.product.get_absolute_url()).status_code, 404)
        self.shop.is_active = False
        self.shop.save()
        self.assertEqual(self.client.get("/ayse/").status_code, 404)

    def test_prices_can_be_hidden(self):
        self.assertContains(self.client.get("/ayse/"), "1.500 ₺")
        self.shop.show_prices = False
        self.shop.save()
        self.assertNotContains(self.client.get("/ayse/"), "1.500 ₺")

    def test_product_page_counts_views(self):
        r = self.client.get(self.product.get_absolute_url())
        self.assertContains(r, "wa.me/905321112233")
        self.product.refresh_from_db()
        self.assertEqual(self.product.view_count, 1)

    def test_product_of_other_shop_is_not_reachable(self):
        self.assertEqual(self.client.get(f"/ayse/urun/{self.foreign.slug}/").status_code, 404)

    def test_qr_redirect_counts_scans(self):
        r = self.client.get(f"/q/{self.shop.qr_code}/")
        self.assertRedirects(r, "/ayse/")
        r = self.client.get(f"/q/{self.shop.qr_code}/?u={self.product.pk}")
        self.assertRedirects(r, self.product.get_absolute_url())
        # başka mağazanın ürünü verilirse mağaza ana sayfasına düşer
        r = self.client.get(f"/q/{self.shop.qr_code}/?u={self.foreign.pk}")
        self.assertRedirects(r, "/ayse/")
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.scan_count, 3)

    def test_custom_design_request(self):
        url = "/ayse/ozel-dikim/"
        self.assertEqual(self.client.get(url).status_code, 404)  # ürün ve renk yokken kapalı
        item = CustomItem.objects.create(shop=self.shop, kind="nevresim", name="Nevresim")
        color = FabricColor.objects.create(shop=self.shop, name="Lacivert", hex="#112233")
        foreign_color = FabricColor.objects.create(shop=self.other, name="Gizli", hex="#000000")
        self.assertContains(self.client.get(url), "viz-config")

        data = {
            "item": item.pk,
            "dims": json.dumps({"w": 9999, "l": 200, "h": "abc"}),
            "parts": json.dumps({"duvet": color.pk, "sheet": foreign_color.pk}),
            "customer_name": "Mehmet",
            "phone": "0532 000 00 00",
        }
        self.assertRedirects(self.client.post(url, data), url + "?ok=1")
        req = CustomRequest.objects.get()
        self.assertEqual(req.dims, {"Yatak eni": 240, "Yatak boyu": 200, "Yatak yüksekliği": 25})
        self.assertEqual(req.colors, {"Nevresim": "Lacivert"})  # başka mağazanın rengi kabul edilmez

        self.client.post(url, {**data, "phone": "123"})  # geçersiz telefon
        self.client.post(url, {**data, "website": "spam"})  # bot tuzağı
        self.assertEqual(CustomRequest.objects.count(), 1)


class PanelTests(Base):
    def setUp(self):
        super().setUp()
        self.client.login(username="ayse", password="gizli-sifre-1")

    def test_login_required(self):
        self.client.logout()
        r = self.client.get(reverse("panel:products"))
        self.assertRedirects(r, "/panel/giris/?next=/panel/urunler/")

    def test_user_without_shop(self):
        get_user_model().objects.create_user("bos", password="gizli-sifre-2")
        self.client.login(username="bos", password="gizli-sifre-2")
        self.assertEqual(self.client.get(reverse("panel:dashboard")).status_code, 403)

    def test_all_pages_render(self):
        for name in ["dashboard", "products", "product_new", "categories", "colors", "custom_items",
                     "requests", "settings", "qr", "qr_poster", "password"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"panel:{name}")).status_code, 200)
        self.assertEqual(self.client.get(reverse("panel:product_edit", args=[self.product.pk])).status_code, 200)

    def test_create_product_with_photos(self):
        r = self.client.post(reverse("panel:product_new"), {
            "name": "Çiçekli Nevresim", "price": "799.90", "category": self.cat.pk,
            "in_stock": "on", "is_active": "on", "new_images": [png("a.png"), png("b.png")],
        })
        product = Product.objects.get(name="Çiçekli Nevresim")
        self.assertRedirects(r, reverse("panel:product_edit", args=[product.pk]))
        self.assertEqual(product.shop, self.shop)
        self.assertEqual(product.slug, "cicekli-nevresim")
        images = list(product.images.all())
        self.assertEqual(len(images), 2)
        with Image.open(images[0].image.path) as im:
            self.assertEqual(im.format, "WEBP")
            self.assertLessEqual(max(im.size), 1600)
        # fotoğraf akışı: boyutlar kaydedilir, oran CSS için noktalı (virgülsüz) yazılır
        self.assertEqual((images[0].thumb_w, images[0].thumb_h), (600, 360))
        html = self.client.get("/ayse/").content.decode()
        self.assertRegex(html, r'data-ratio="1\.400"')  # 600/360=1.67 → en çok 1.4'e sınırlanır
        self.assertNotRegex(html, r'data-ratio="\d,')
        # ikinci fotoğrafı kapak yap, sonra sil
        self.client.post(reverse("panel:image_cover", args=[images[1].pk]))
        self.assertEqual(product.images.first().pk, images[1].pk)
        self.client.post(reverse("panel:image_delete", args=[images[1].pk]))
        self.assertEqual(product.images.count(), 1)

    def test_rejects_non_image_upload(self):
        bad = SimpleUploadedFile("x.png", b"resim degil", content_type="image/png")
        r = self.client.post(reverse("panel:product_new"), {"name": "X", "new_images": [bad]})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Product.objects.filter(name="X").exists())

    def test_old_price_must_be_higher(self):
        r = self.client.post(reverse("panel:product_new"), {"name": "Y", "price": "100", "old_price": "90"})
        self.assertContains(r, "Eski fiyat, güncel fiyattan yüksek olmalı")

    def test_toggle_and_delete(self):
        self.client.post(reverse("panel:product_toggle", args=[self.product.pk]), {"field": "in_stock"})
        self.product.refresh_from_db()
        self.assertFalse(self.product.in_stock)
        self.client.post(reverse("panel:product_delete", args=[self.product.pk]))
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_cannot_touch_other_shops_data(self):
        pk = self.foreign.pk
        self.assertEqual(self.client.get(reverse("panel:product_edit", args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("panel:product_delete", args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("panel:product_toggle", args=[pk]), {"field": "is_active"}).status_code, 404)
        self.assertEqual(self.client.get(reverse("panel:qr_image", args=["png"]) + f"?u={pk}").status_code, 404)
        foreign_cat = Category.objects.create(shop=self.other, name="Onların")
        self.assertEqual(self.client.post(reverse("panel:delete", args=["kategori", foreign_cat.pk])).status_code, 404)
        # başka mağazanın kategorisi ürün formunda seçilemez
        self.client.post(reverse("panel:product_edit", args=[self.product.pk]), {"name": "Ütü", "category": foreign_cat.pk})
        self.product.refresh_from_db()
        self.assertEqual(self.product.category, self.cat)
        # mağaza değiştirme de yalnızca üyesi olunan mağazaya izin verir
        self.assertEqual(self.client.post(reverse("panel:switch"), {"shop": self.other.pk}).status_code, 404)
        self.assertNotContains(self.client.get(reverse("panel:products")), "Yabancı Ürün")

    def test_simple_crud(self):
        self.client.post(reverse("panel:categories"), {"name": "Havlu", "order": 2})
        cat = Category.objects.get(name="Havlu")
        self.assertEqual(cat.shop, self.shop)
        self.client.post(reverse("panel:edit", args=["kategori", cat.pk]), {"name": "Havlular", "order": 1})
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Havlular")
        self.client.post(reverse("panel:colors"), {"name": "Mavi", "hex": "#0000ff", "pattern": "duz", "hex2": "#ffffff", "order": 0})
        self.assertTrue(self.shop.fabric_colors.filter(name="Mavi").exists())
        self.client.post(reverse("panel:custom_items"), {"kind": "perde", "name": "Tül", "order": 0, "is_active": "on"})
        self.assertTrue(self.shop.custom_items.filter(name="Tül").exists())
        self.client.post(reverse("panel:delete", args=["kategori", cat.pk]))
        self.assertFalse(Category.objects.filter(pk=cat.pk).exists())

    def test_settings_and_qr(self):
        r = self.client.post(reverse("panel:settings"), {
            "name": "Ayşe Ev Tekstili", "theme": "gece", "show_prices": "on", "logo": png("logo.png"),
        })
        self.assertRedirects(r, reverse("panel:settings"))
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.name, "Ayşe Ev Tekstili")
        self.assertTrue(self.shop.logo.name.endswith(".webp"))
        self.assertEqual(self.shop.theme, "gece")
        self.assertContains(self.client.get("/ayse/"), "color-scheme: dark")
        r = self.client.post(reverse("panel:settings"), {"name": "A", "theme": "yok-boyle-tema"})
        self.assertEqual(r.status_code, 200)  # tanımsız tema reddedilir
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.theme, "gece")

        png_qr = self.client.get(reverse("panel:qr_image", args=["png"]))
        self.assertEqual(png_qr["Content-Type"], "image/png")
        self.assertTrue(png_qr.content.startswith(b"\x89PNG"))
        svg = self.client.get(reverse("panel:qr_image", args=["svg"]) + "?indir=1")
        self.assertIn("attachment", svg["Content-Disposition"])
        self.assertContains(self.client.get(reverse("panel:qr")), f"/q/{self.shop.qr_code}/")


class SecurityTests(Base):
    """Güvenlik denetiminde bulunan açıkların ve zayıflıkların regresyon testleri."""

    def custom_setup(self):
        item = CustomItem.objects.create(shop=self.shop, kind="nevresim", name="Nevresim")
        color = FabricColor.objects.create(shop=self.shop, name="Lacivert", hex="#112233")
        return item, color

    def post_request(self, item, color, **extra):
        data = {
            "item": item.pk, "dims": json.dumps({"w": 160}), "parts": json.dumps({"duvet": color.pk}),
            "customer_name": "Mehmet", "phone": "0532 000 00 00", **extra,
        }
        return self.client.post("/ayse/ozel-dikim/", data)

    # --- çökme (500) açıkları ---
    def test_unicode_digits_in_id_params_do_not_crash(self):
        # "²".isdigit() True ama int() edilemez; eskiden 500 veriyordu
        self.client.get(f"/q/{self.shop.qr_code}/", {"u": "²"})
        self.client.login(username="ayse", password="gizli-sifre-1")
        self.assertEqual(self.client.get(reverse("panel:qr"), {"u": "²"}).status_code, 200)  # geçersiz kimlik yok sayılır
        self.assertEqual(self.client.get(reverse("panel:products"), {"kategori": "²"}).status_code, 200)

    def test_custom_request_survives_hostile_json(self):
        item, color = self.custom_setup()
        for dims in ['{"w": 1e999}', "[" * 100000, '{"w": NaN}', '{"w": [1]}', "null"]:
            with self.subTest(dims=dims[:20]):
                r = self.client.post("/ayse/ozel-dikim/", {
                    "item": item.pk, "dims": dims, "parts": "{}",
                    "customer_name": "A", "phone": "0532 000 00 00",
                })
                self.assertIn(r.status_code, (200, 302))
                cache.clear()

    # --- kötüye kullanım / hız sınırı ---
    def test_custom_request_is_rate_limited(self):
        item, color = self.custom_setup()
        for _ in range(8):
            self.post_request(item, color)
        self.assertEqual(CustomRequest.objects.count(), 5)

    def test_login_is_throttled(self):
        for _ in range(5):
            r = self.client.post(reverse("panel:login"), {"username": "ayse", "password": "yanlis"})
            self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse("panel:login"), {"username": "ayse", "password": "gizli-sifre-1"})
        self.assertEqual(r.status_code, 429)  # doğru şifre bile bekletilir
        self.assertIn("Retry-After", r)
        # başka bir kullanıcı adı aynı IP'den hâlâ deneyebilir (ip sınırı daha yüksek)
        r = self.client.post(reverse("panel:login"), {"username": "baska", "password": "x"})
        self.assertEqual(r.status_code, 200)

    def test_successful_login_resets_user_counter(self):
        for _ in range(3):
            self.client.post(reverse("panel:login"), {"username": "ayse", "password": "yanlis"})
        r = self.client.post(reverse("panel:login"), {"username": "ayse", "password": "gizli-sifre-1"})
        self.assertEqual(r.status_code, 302)

    def test_forwarded_header_ignored_unless_behind_proxy(self):
        from unittest import mock

        from .utils import client_ip

        request = mock.Mock(META={"REMOTE_ADDR": "10.0.0.1", "HTTP_X_FORWARDED_FOR": "6.6.6.6, 1.2.3.4"})
        with override_settings(BEHIND_PROXY=False):
            self.assertEqual(client_ip(request), "10.0.0.1")
        with override_settings(BEHIND_PROXY=True):
            self.assertEqual(client_ip(request), "1.2.3.4")  # sahte soldaki değil, vekilin eklediği sağdaki

    def test_search_is_bounded(self):
        from .utils import search_words

        self.assertLessEqual(len(search_words("a " * 500)), 6)
        self.assertEqual(self.client.get("/ayse/", {"q": "x " * 500}).status_code, 200)

    # --- yükleme sınırları ---
    @override_settings(MAX_IMAGE_MB=0.001)
    def test_upload_size_limit_applies_to_every_image_field(self):
        self.client.login(username="ayse", password="gizli-sifre-1")
        r = self.client.post(reverse("panel:settings"), {"name": "A", "theme": "kum", "logo": png("l.png")})
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse("panel:colors"), {
            "name": "K", "hex": "#000000", "pattern": "duz", "hex2": "#ffffff", "order": 0, "image": png("k.png"),
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(FabricColor.objects.filter(name="K").exists())
        r = self.client.post(reverse("panel:product_new"), {"name": "Z", "new_images": [png("p.png")]})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Product.objects.filter(name="Z").exists())

    @override_settings(MAX_IMAGE_PIXELS=1000)
    def test_pixel_limit_blocks_decompression_bombs(self):
        self.client.login(username="ayse", password="gizli-sifre-1")
        r = self.client.post(reverse("panel:product_new"), {"name": "Z", "new_images": [png("p.png")]})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Product.objects.filter(name="Z").exists())

    @override_settings(MAX_REQUEST_MB=1)
    def test_oversized_request_rejected_early(self):
        self.client.login(username="ayse", password="gizli-sifre-1")
        r = self.client.post(reverse("panel:product_new"), {"name": "Z", "x": "a" * (2 * 1024 * 1024)})
        self.assertEqual(r.status_code, 413)

    # --- tarayıcı korumaları ---
    def test_security_headers(self):
        r = self.client.get("/ayse/")
        csp = r["Content-Security-Policy"]
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp.split("script-src")[1].split(";")[0])
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertEqual(r["X-Frame-Options"], "DENY")
        self.assertIn("Permissions-Policy", r)

    def test_no_inline_event_handlers_anywhere(self):
        import re

        self.client.login(username="ayse", password="gizli-sifre-1")
        pages = ["/ayse/", self.product.get_absolute_url(), "/panel/", "/panel/urunler/", "/panel/qr/afis/",
                 f"/panel/urunler/{self.product.pk}/", "/panel/kategoriler/", "/panel/renkler/",
                 "/panel/ozel-dikim/", "/panel/talepler/", "/panel/ayarlar/"]
        for url in pages:
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertIsNone(re.search(r"\son[a-z]+\s*=", html), "satır içi olay işleyicisi var")
                self.assertNotIn("javascript:", html)

    def test_panel_pages_are_not_cached(self):
        self.client.login(username="ayse", password="gizli-sifre-1")
        self.assertIn("no-store", self.client.get("/panel/")["Cache-Control"])

    def test_foreign_host_header_rejected(self):
        with override_settings(ALLOWED_HOSTS=["testserver"]):
            self.assertEqual(self.client.get("/ayse/", HTTP_HOST="evil.example").status_code, 400)

    def test_demo_command_refuses_outside_debug(self):
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            call_command("demo_yukle")
