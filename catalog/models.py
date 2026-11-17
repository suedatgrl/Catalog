from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

from .kinds import KIND_CHOICES, KINDS
from .utils import make_code, normalize, text_on, tr_slugify, unique_slug, whatsapp_number

RESERVED_SLUGS = {"panel", "admin", "q", "media", "static", "giris", "api", "hakkinda"}

hex_validator = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Renk #RRGGBB biçiminde olmalı (örn. #1d4ed8).")


def shop_upload(instance, filename):
    return f"shops/{instance.shop_ref}/{instance.upload_folder}/{filename}"


class Shop(models.Model):
    """Platformdaki her esnaf / işletme bir mağazadır (kiracı)."""

    name = models.CharField("Mağaza adı", max_length=80)
    slug = models.SlugField(
        "Adres", max_length=60, unique=True, help_text="Mağazanın web adresi: site.com/<adres>/"
    )
    qr_code = models.CharField(max_length=12, unique=True, default=make_code, editable=False)
    tagline = models.CharField("Slogan", max_length=120, blank=True)
    description = models.TextField("Hakkında", blank=True)
    logo = models.ImageField("Logo", upload_to=shop_upload, blank=True)
    phone = models.CharField("Telefon", max_length=20, blank=True)
    whatsapp = models.CharField(
        "WhatsApp numarası", max_length=20, blank=True, help_text="Örn. 0532 111 22 33"
    )
    instagram = models.CharField("Instagram kullanıcı adı", max_length=40, blank=True)
    address = models.CharField("Adres (açık)", max_length=200, blank=True)
    working_hours = models.CharField("Çalışma saatleri", max_length=80, blank=True)
    accent_color = models.CharField(
        "Tema rengi", max_length=7, default="#0f766e", validators=[hex_validator]
    )
    show_prices = models.BooleanField("Fiyatları göster", default=True)
    custom_enabled = models.BooleanField("Özel dikim sayfası açık", default=True)
    is_active = models.BooleanField("Yayında", default=True)
    scan_count = models.PositiveIntegerField("QR okutma sayısı", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    upload_folder = "brand"

    class Meta:
        verbose_name = "Mağaza"
        verbose_name_plural = "Mağazalar"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def shop_ref(self):
        return self.qr_code

    def clean(self):
        if self.slug in RESERVED_SLUGS:
            raise ValidationError({"slug": "Bu adres kullanılamaz, başka bir adres seçin."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Shop.objects.all(), self.name, "magaza", 60)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:shop", args=[self.slug])

    @property
    def accent_text(self):
        return text_on(self.accent_color)

    @property
    def wa_number(self):
        return whatsapp_number(self.whatsapp)

    @property
    def instagram_handle(self):
        return self.instagram.strip().lstrip("@").rstrip("/").split("/")[-1]


class ShopMember(models.Model):
    """Bir kullanıcının bir mağazanın panelini yönetme yetkisi."""

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shop_memberships"
    )

    class Meta:
        verbose_name = "Mağaza yetkilisi"
        verbose_name_plural = "Mağaza yetkilileri"
        constraints = [models.UniqueConstraint(fields=["shop", "user"], name="uniq_shop_member")]

    def __str__(self):
        return f"{self.user} → {self.shop}"


class Category(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField("Kategori adı", max_length=60)
    slug = models.SlugField(max_length=80)
    order = models.PositiveIntegerField("Sıra", default=0)

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"
        ordering = ["order", "name"]
        constraints = [models.UniqueConstraint(fields=["shop", "slug"], name="uniq_category_slug")]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self.shop.categories.all(), self.name, "kategori")
        super().save(*args, **kwargs)
        # Kategori adı ürün aramasına dahil; ad değişince ürünlerin arama metni yenilenir.
        for product in self.products.all():
            product.save(update_fields=["search_text"])


class Product(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(
        Category,
        verbose_name="Kategori",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField("Ürün adı", max_length=120)
    slug = models.SlugField(max_length=80)
    description = models.TextField("Açıklama", blank=True)
    price = models.DecimalField(
        "Fiyat (₺)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Boş bırakırsanız “Fiyat için sorunuz” yazar.",
    )
    old_price = models.DecimalField(
        "Eski fiyat (₺)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="İndirim göstermek için doldurun.",
    )
    sku = models.CharField("Stok / ürün kodu", max_length=40, blank=True)
    sizes = models.CharField(
        "Bedenler / ölçüler", max_length=200, blank=True, help_text="Virgülle ayırın: S, M, L, XL"
    )
    colors = models.CharField(
        "Renk seçenekleri", max_length=200, blank=True, help_text="Virgülle ayırın: Beyaz, Lacivert"
    )
    specs = models.TextField(
        "Teknik özellikler",
        blank=True,
        help_text="Her satıra bir özellik yazın. Örn. “Güç: 2400 W”",
    )
    is_active = models.BooleanField("Yayında", default=True)
    is_featured = models.BooleanField("Öne çıkar", default=False)
    in_stock = models.BooleanField("Stokta var", default=True)
    view_count = models.PositiveIntegerField(default=0)
    search_text = models.TextField(editable=False, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"
        ordering = ["-is_featured", "-created_at"]
        constraints = [models.UniqueConstraint(fields=["shop", "slug"], name="uniq_product_slug")]
        indexes = [models.Index(fields=["shop", "is_active"])]

    def __str__(self):
        return self.name

    def clean(self):
        if self.old_price is not None and self.price is not None and self.old_price <= self.price:
            raise ValidationError({"old_price": "Eski fiyat, güncel fiyattan yüksek olmalı."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self.shop.products.all(), self.name)
        cat = self.category.name if self.category_id else ""
        self.search_text = normalize(
            f"{self.name} {self.sku} {cat} {self.colors} {self.sizes} {self.description} {self.specs}"
        )
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product", args=[self.shop.slug, self.slug])

    @staticmethod
    def _split(value):
        return [v.strip() for v in value.split(",") if v.strip()]

    @property
    def size_list(self):
        return self._split(self.sizes)

    @property
    def color_list(self):
        return self._split(self.colors)

    @property
    def spec_rows(self):
        rows = []
        for line in self.specs.splitlines():
            line = line.strip()
            if not line:
                continue
            key, sep, val = line.partition(":")
            rows.append((key.strip(), val.strip()) if sep else ("", line))
        return rows

    @property
    def discount_percent(self):
        if self.price and self.old_price and self.old_price > self.price:
            return round((1 - self.price / self.old_price) * 100)
        return 0

    @property
    def cover(self):
        """İlk görsel (liste görünümlerinde prefetch edilmiş veriyi kullanır)."""
        images = list(self.images.all())
        return images[0] if images else None


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=shop_upload)
    thumb = models.ImageField(upload_to=shop_upload)
    order = models.PositiveIntegerField(default=0)

    upload_folder = "products"

    class Meta:
        ordering = ["order", "id"]

    @property
    def shop_ref(self):
        return self.product.shop.qr_code


class FabricColor(models.Model):
    """Özel dikimde müşteriye sunulan kumaş / renk kartelası."""

    PATTERNS = [
        ("duz", "Düz"),
        ("cizgili", "Çizgili"),
        ("kareli", "Kareli"),
        ("puantiye", "Puantiyeli"),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="fabric_colors")
    name = models.CharField("Renk / kumaş adı", max_length=50)
    hex = models.CharField("Renk", max_length=7, default="#e5e7eb", validators=[hex_validator])
    pattern = models.CharField("Desen", max_length=10, choices=PATTERNS, default="duz")
    hex2 = models.CharField(
        "Desen rengi", max_length=7, default="#ffffff", validators=[hex_validator]
    )
    image = models.ImageField(
        "Kumaş fotoğrafı",
        upload_to=shop_upload,
        blank=True,
        help_text="İsteğe bağlı. Yüklerseniz çizimde renk yerine bu kumaş kullanılır.",
    )
    order = models.PositiveIntegerField("Sıra", default=0)

    upload_folder = "fabrics"

    class Meta:
        verbose_name = "Kumaş rengi"
        verbose_name_plural = "Kumaş renkleri"
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    @property
    def shop_ref(self):
        return self.shop.qr_code


class CustomItem(models.Model):
    """Mağazanın ölçüye özel diktiği ürün (nevresim, koltuk örtüsü, perde...)."""

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="custom_items")
    kind = models.CharField("Tür", max_length=20, choices=KIND_CHOICES)
    name = models.CharField("Görünen ad", max_length=60, help_text="Örn. Ranforce nevresim takımı")
    description = models.CharField("Kısa açıklama", max_length=200, blank=True)
    base_price = models.DecimalField(
        "Sabit işçilik (₺)", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    price_per_m2 = models.DecimalField(
        "Kumaş m² fiyatı (₺)", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Doldurursanız müşteriye tahmini fiyat gösterilir. Boşsa fiyat gösterilmez.",
    )
    is_active = models.BooleanField("Yayında", default=True)
    order = models.PositiveIntegerField("Sıra", default=0)

    class Meta:
        verbose_name = "Özel dikim ürünü"
        verbose_name_plural = "Özel dikim ürünleri"
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    @property
    def kind_info(self):
        return KINDS[self.kind]


class CustomRequest(models.Model):
    """Müşterinin özel dikim sayfasından gönderdiği teklif talebi."""

    STATUSES = [("yeni", "Yeni"), ("gorusuldu", "Görüşüldü"), ("tamam", "Tamamlandı")]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="custom_requests")
    item = models.ForeignKey(CustomItem, on_delete=models.SET_NULL, null=True, blank=True)
    item_name = models.CharField(max_length=80)
    dims = models.JSONField(default=dict)  # {"Yatak eni": 160, ...}
    colors = models.JSONField(default=dict)  # {"Nevresim": "Lacivert", ...}
    customer_name = models.CharField("Ad soyad", max_length=80)
    phone = models.CharField("Telefon", max_length=20)
    note = models.CharField("Not", max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="yeni")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Özel dikim talebi"
        verbose_name_plural = "Özel dikim talepleri"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer_name} — {self.item_name}"

    @property
    def wa_number(self):
        return whatsapp_number(self.phone)


@receiver(post_delete, sender=ProductImage)
def _delete_product_files(sender, instance, **kwargs):
    for f in (instance.image, instance.thumb):
        if f:
            f.delete(save=False)


@receiver(post_delete, sender=FabricColor)
def _delete_fabric_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


__all__ = [
    "Shop", "ShopMember", "Category", "Product", "ProductImage",
    "FabricColor", "CustomItem", "CustomRequest", "tr_slugify",
]
