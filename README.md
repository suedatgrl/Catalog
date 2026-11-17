# Vitrin — QR ile açılan çok mağazalı dijital katalog

Esnaf ve işletmeler için ortak altyapılı ürün kataloğu. Müşteri dükkândaki QR kodu okutur, ürünleri
telefonunda görür. Mağaza sahibi ürünlerini kod yazmadan kendi panelinden ekler, düzenler, siler.
Satın alma yoktur (şimdilik); müşteri WhatsApp ya da telefonla mağazaya ulaşır.

- **Müşteri tarafı:** katalog, Türkçe arama, kategori, ürün sayfası, özel dikim önizlemesi
- **Esnaf paneli:** ürün/kategori/fotoğraf yönetimi, renk kartelası, talepler, QR, mağaza ayarları
- **Platform yönetimi (Django admin):** mağaza açma ve kullanıcı tanımlama — yalnızca platform sahibi
- Tek kod tabanı, tek veritabanı; her mağaza bir **kiracıdır** (`Shop`)

## İçindekiler

1. [Teknoloji](#teknoloji)
2. [Kurulum](#kurulum)
3. [Günlük geliştirme](#günlük-geliştirme)
4. [Adres haritası](#adres-haritası)
5. [Proje yapısı](#proje-yapısı)
6. [Veri modeli](#veri-modeli)
7. [Önemli tasarım kararları](#önemli-tasarım-kararları)
8. [Sık yapılan geliştirmeler](#sık-yapılan-geliştirmeler)
9. [Ortam değişkenleri](#ortam-değişkenleri)
10. [Test](#test)
11. [Yayına alma](#yayına-alma)
12. [Güvenlik ve gizlilik notları](#güvenlik-ve-gizlilik-notları)
13. [Bilinen eksikler ve fikirler](#bilinen-eksikler-ve-fikirler)
14. [Yeni esnafı sisteme alma](#yeni-esnafı-sisteme-alma)

## Teknoloji

| Katman | Seçim |
|---|---|
| Dil / çatı | Python 3.10+, Django 5.2 (LTS) |
| Veritabanı | Varsayılan SQLite; `DB_NAME` verilirse PostgreSQL |
| Görsel işleme | Pillow (yüklenen fotoğraflar WebP'ye çevrilip küçültülür) |
| QR kod | segno (PNG ve SVG üretir) |
| Ön yüz | Sunucuda render edilen Django şablonları + sade CSS + az miktarda vanilla JS. Derleme adımı, npm, framework **yok** |
| Yazı tipi | Plus Jakarta Sans (Google Fonts, yalnızca müşteri tarafı; yüklenmezse sistem yazı tipine düşer) |

Bilinçli tercih: ön yüzde bundler ve framework olmaması CI/CD'yi ve devralan geliştiricinin işini
basit tutar. İhtiyaç doğarsa sonradan eklenebilir.

## Kurulum

Gereken: Python 3.10+ ve `venv`.

```bash
git clone https://github.com/suedatgrl/Catalog.git
cd Catalog
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser     # platform yöneticisi (/admin/ için)
.venv/bin/python manage.py demo_yukle          # isteğe bağlı: örnek mağaza + panel kullanıcısı
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

`demo_yukle` şunları kurar: `/ornek-magaza/` mağazası, ürünler, renk kartelası, özel dikim ürünleri ve
**`demo` / `demo12345`** kullanıcısı. Bilinen şifre içerdiği için **üretimde çalıştırmayın.**

### Telefondan deneme

QR kodu telefonla okutabilmek için telefon ve bilgisayar aynı Wi-Fi'da olmalı. `DEBUG=1` iken panel
`127.0.0.1` üzerinden açılsa bile QR kodlar otomatik olarak bilgisayarın yerel ağ adresini
(`http://192.168.x.x:8000`) taşır (`catalog/utils.py → site_url`). `SITE_URL` ayarlıysa her zaman o kullanılır.
Güvenlik duvarı 8000 portunu engelliyorsa telefon bağlanamaz.

## Günlük geliştirme

```bash
.venv/bin/python manage.py runserver 0.0.0.0:8000   # geliştirme sunucusu
.venv/bin/python manage.py test                     # tüm testler (~15 sn)
.venv/bin/python manage.py makemigrations           # model değiştirince
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
```

- Model değiştirdiyseniz **migration dosyasını commit'leyin.**
- Ürün arama metni (`Product.search_text`) kayıt sırasında üretilir. Arama kurallarını değiştirirseniz
  mevcut ürünleri yeniden kaydedin:
  `Product.objects.all()` üzerinde `p.save(update_fields=["search_text"])`.
- `db.sqlite3` ve `media/` git'e girmez (`.gitignore`).

## Adres haritası

| Adres | Kim | Ne |
|---|---|---|
| `/` | herkes | Platform tanıtım sayfası |
| `/<mağaza-adresi>/` | müşteri | Katalog. `?q=` arama, `?kategori=` filtre, `?sayfa=` sayfalama |
| `/<mağaza-adresi>/urun/<slug>/` | müşteri | Ürün sayfası |
| `/<mağaza-adresi>/ozel-dikim/` | müşteri | Özel dikim önizlemesi (GET) ve teklif talebi (POST). `?urun=<id>` ile belirli ürün seçili açılır |
| `/q/<kod>/` | müşteri | **QR'ların gittiği adres.** Okutmayı sayar, mağazaya yönlendirir. `?u=<ürün id>` ürüne yönlendirir |
| `/panel/` | esnaf | Özet; altında `urunler/`, `kategoriler/`, `ozel-dikim/`, `renkler/`, `talepler/`, `qr/`, `ayarlar/` |
| `/admin/` | platform sahibi | Mağaza ve kullanıcı yönetimi |

Mağaza adresleri kök dizinde olduğu için `config/urls.py` içinde `catalog.urls` **en sona** eklenir ve
`catalog/models.py → RESERVED_SLUGS` (`panel`, `admin`, `q`, `media`, `static`, …) mağaza adı olarak
kullanılamaz. Yeni bir kök adres eklerseniz bu listeye de ekleyin.

## Proje yapısı

```
config/                 Django ayarları, kök urls, wsgi/asgi
catalog/                Müşteri tarafı + veri modelleri
  models.py             Shop, ShopMember, Category, Product, ProductImage,
                        FabricColor, CustomItem, CustomRequest
  views.py              katalog, ürün, QR yönlendirme, özel dikim (+ talep kaydı)
  kinds.py              Özel dikim türleri: şekil, ölçü sınırları, parçalar, hazır ölçüler
  themes.py             Mağaza renk temaları (hazır paletler)
  utils.py              Türkçe slug/arama, görsel işleme, WhatsApp numarası, site_url
  admin.py              Platform yönetim ekranı
  templatetags/         `tl` (para biçimi), `wa_link`, `initial`
  management/commands/  demo_yukle
  tests.py              Tüm testler (müşteri + panel + yalıtım)
panel/                  Esnaf paneli
  views.py              Her görünüm `@panel_view` ile sarılı → request.shop
  forms.py              Formlar; ShopFormMixin kayıtları mağazaya bağlar
  urls.py
templates/store/        Müşteri şablonları
templates/panel/        Panel şablonları
static/css/             store.css (müşteri), panel.css (esnaf)
static/js/              store.js (daha fazla yükle, galeri, paylaş), visualizer.js (özel dikim çizimi)
```

## Veri modeli

```
Shop 1─* ShopMember *─1 User          kim hangi mağazayı yönetir (çoktan çoğa)
Shop 1─* Category
Shop 1─* Product 1─* ProductImage     image (1600px) + thumb (600px), ikisi de WebP
Shop 1─* FabricColor                  özel dikim renk/kumaş kartelası
Shop 1─* CustomItem                   özel dikim ürün türü (nevresim, perde, …)
Shop 1─* CustomRequest                müşterinin gönderdiği teklif talebi
```

Dikkat edilecekler:

- **Her tablonun `shop` alanı vardır;** mağazalar arası veri paylaşılmaz.
- `Shop.qr_code`: rastgele, değişmeyen kısa kod. QR kodlar `slug`'a değil bu koda bağlıdır; mağaza adresi
  değişse bile basılı kodlar çalışır.
- `Shop.theme`: `catalog/themes.py` içindeki bir anahtar. (Önceki `accent_color` alanı 0002 migration'ı ile kaldırıldı.)
- `Product.search_text`: ad, kod, kategori, renk, beden, açıklama, teknik özelliklerin sadeleştirilmiş hâli (aşağıya bakın).
- `Product.price` boş olabilir → "Fiyat için sorunuz" gösterilir. `Shop.show_prices` kapalıysa hiçbir fiyat gösterilmez.
- Yüklenen görseller `media/shops/<qr_code>/<products|fabrics|brand>/<uuid>.webp` altında tutulur.
- `CustomRequest` içindeki ölçü ve renkler JSON olarak, **talep anının etiketleriyle** saklanır; sonradan
  ürün/renk silinse bile talep okunur kalır.

## Önemli tasarım kararları

### Kiracı yalıtımı (en kritik kural)

Panel görünümlerinin hepsi `@panel_view` ile sarılıdır: giriş ister, kullanıcının aktif mağazasını bulup
`request.shop` yapar, mağazası yoksa 403 verir. **Panelde her sorgu `shop=request.shop` ile süzülmelidir.**
Yeni bir panel görünümü yazarken:

```python
@panel_view
def my_view(request, pk):
    obj = get_object_or_404(MyModel, pk=pk, shop=request.shop)   # ← shop süzgeci şart
```

Formlar `ShopFormMixin` ile mağazaya bağlanır; seçim alanlarının (ör. kategori) `queryset`'i mağazayla
sınırlanmalıdır (bkz. `ProductForm.__init__`). `catalog/tests.py → test_cannot_touch_other_shops_data`
bu kuralı denetler; yeni bir uç eklediğinizde oraya bir satır ekleyin.

Kullanıcı ↔ mağaza ilişkisi `ShopMember` ile kurulur. Süper kullanıcı tüm mağazaları panelde görebilir.

### Türkçe arama (`catalog/utils.py`)

`normalize()` hem ürün metnini hem müşterinin yazdığını aynı biçime getirir: Türkçe harfler
sadeleştirilir (`ı→i, ş→s, ğ→g, ü→u, ö→o, ç→c`), şapkalı harfler ve ayrık işaretler (NFKD) temizlenir,
küçük harfe çevrilir. `search_words()` ayrıca uzun kelimelerdeki `-ler/-lar` ekini atar.
Böylece `ÇARŞAF`, `çarşaf`, `carsaf`, `havlular` aynı sonucu verir. `.lower()` Türkçe `İ/I` ayrımında
yanlış sonuç verdiği için önce harf eşlemesi yapılır — bu sırayı bozmayın.
Arama basit `contains` süzgecidir (kelime başına bir `AND`); on binlerce ürün için tam metin aramaya
(PostgreSQL `tsvector`/trigram) geçilmelidir.

### Görsel hattı

Yüklenen her fotoğraf `process_image()` ile döndürülür (EXIF), RGB'ye çevrilir, 1600px (büyük) ve 600px
(liste) olarak küçültülüp WebP kaydedilir. Böylece 10 MB'lık telefon fotoğrafı mobilde hızlı açılır.
Sınırlar `settings.py`: `MAX_IMAGE_MB`, `MAX_IMAGES_PER_PRODUCT`. Dosya türü `forms.ImageField` ile
Pillow tarafından doğrulanır (uzantıya güvenilmez). Silinen kayıtların dosyaları `post_delete`
sinyalleriyle temizlenir.

### QR kodlar

- Mağaza QR'ı: `<SITE_URL>/q/<qr_code>/` → okutma sayacı artar → mağazaya yönlendirir.
- Ürün raf etiketi: aynı adres + `?u=<ürün id>` → doğrudan ürün sayfası. Başka mağazanın ürün id'si verilirse
  mağaza ana sayfasına düşer.
- PNG ve SVG panelden indirilir; ayrıca yazdırılabilir A4 afiş vardır (`templates/panel/qr_poster.html`).
- **QR'ın içine yazılan kök adres `SITE_URL`'dir.** Geliştirmede yerel ağ adresi kullanılır (yukarıya bakın).
  Üretimde kodlar basılmadan önce `SITE_URL` kesinleşmelidir; alan adı değişirse basılı kodlar bozulur.

### Temalar

Müşteri tarafının renkleri `catalog/themes.py` içindeki hazır paletlerden gelir; esnaf serbest renk seçmez
(her mağazanın derli toplu görünmesi için). Seçilen tema `<body style="--bg: …; --accent: …">` olarak
CSS değişkenlerine yazılır (`Shop.theme_style`), `store.css` yalnızca bu değişkenleri kullanır.
Yeni tema eklemek için `THEMES` sözlüğüne bir kayıt yeterlidir (migration gerekmez; `choices` koddan gelir).
Özel dikim çizim alanı her temada **beyaz zeminlidir**; kumaş renkleri bozulmasın diye.
Koyu bir tema (`gece`) varsa `scheme: "dark"` olarak işaretlenir.

### Özel dikim

Esnaf **renk kartelasını** (`FabricColor`: düz, çizgili, kareli, puantiyeli veya kumaş fotoğrafı) ve
sunduğu **ürün türlerini** (`CustomItem`: nevresim, lastikli çarşaf, yatak örtüsü, koltuk, perde, masa
örtüsü, minder) girer. Müşteri ölçüyü ve renkleri seçer, çizim anında güncellenir
(`static/js/visualizer.js`, SVG, gerçek orana göre). Sayfa, en az bir aktif ürün **ve** bir renk varsa açılır;
yoksa 404.

- `kinds.py` her türün ölçülerini (anahtar, etiket, en az, en çok, varsayılan), renk verilecek parçalarını
  ve hazır ölçülerini tanımlar. Sunucu, tarayıcıdan gelen ölçüleri **bu sınırlara göre yeniden kırpar**.
- Kumaş (m²) ve fiyat tahmini `visualizer.js → AREA` içindeki kaba formüllerle hesaplanır (dikiş payı,
  pile oranı vb.). Bunlar fikir vermek içindir; gerçek terzilik hesabıyla doğrulanması gerekir.
- Esnaf `price_per_m2` girmezse müşteriye fiyat gösterilmez.
- Talep: `CustomRequest` olarak kaydedilir (panelde "Talepler"). Müşteri ayrıca aynı bilgileri hazır
  WhatsApp mesajı olarak da gönderebilir. Form bot tuzağı (gizli `website` alanı) içerir; doldurulursa talep
  sessizce yok sayılır.

### Telefon numaraları

`whatsapp_number()` Türkiye biçimlerini `wa.me` biçimine çevirir (`0532 111 22 33` → `905321112233`).
Esnaf WhatsApp ve telefon numarasını panelde **Mağaza ayarları → İletişim** bölümünden kendisi değiştirir.

## Sık yapılan geliştirmeler

**Yeni özel dikim türü:** `kinds.py → KINDS` içine kayıt ekleyin; `visualizer.js` içinde `SHAPES` (çizim) ve
`AREA` (kumaş hesabı) anahtarlarını aynı adla ekleyin. Mevcut bir `shape`'i (`bed`, `sofa`, `curtain`,
`table`, `cushion`) yeniden kullanıyorsanız çizim kodu gerekmez. `choices` koddan geldiği için migration çıkabilir
(`makemigrations` çalıştırın).

**Yeni tema:** `themes.py → THEMES`.

**Ürüne yeni alan:** `models.py` → `makemigrations` → `panel/forms.py → ProductForm.Meta.fields` →
`templates/panel/product_form.html` (alanı doğru karta ekleyin) → `templates/store/product.html`. Aranabilir
olacaksa `Product.save()` içindeki `search_text`'e ekleyin.

**Yeni panel sayfası:** `panel/views.py` (`@panel_view`, `shop=request.shop`) → `panel/urls.py` →
`templates/panel/` → `templates/panel/base.html` menüsüne bağlantı → `test_cannot_touch_other_shops_data`'ya
yalıtım satırı. Kategori/renk/özel dikim gibi basit liste+ekle+düzenle+sil sayfaları `panel/views.py → SIMPLE` sözlüğüne
kayıt eklenerek yapılır.

**Para biçimi:** `{{ değer|tl }}` (`1.299 ₺` / `1.299,90 ₺`).

## Ortam değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `DJANGO_DEBUG` | `1` | Üretimde `0`. `0` iken güvenli çerezler ve proxy başlığı açılır |
| `DJANGO_SECRET_KEY` | geliştirmede sabit anahtar | **`DEBUG=0` iken zorunlu**, yoksa uygulama başlamaz |
| `DJANGO_ALLOWED_HOSTS` | `DEBUG=1` ise `*` | Virgülle ayrılmış alan adları |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | boş | Örn. `https://ornek.com` (HTTPS arkasında gerekir) |
| `SITE_URL` | istekten türetilir | QR kodlara yazılan kök adres, örn. `https://ornek.com` (sonunda `/` olmadan) |
| `PLATFORM_NAME` | `Vitrin` | Başlıklarda ve girişte görünen platform adı |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | boş | `DB_NAME` verilirse PostgreSQL. `requirements.txt` içindeki `psycopg` satırını açın |
| `MEDIA_ROOT` | `./media` | Yüklenen dosyaların kalıcı diski |

## Test

```bash
.venv/bin/python manage.py test
```

Testler `catalog/tests.py` içindedir ve geçici bir medya klasörü kullanır. Kapsam: yardımcı fonksiyonlar,
Türkçe arama, müşteri sayfaları, gizli ürün/mağaza, QR yönlendirme ve sayaç, özel dikim talebinin sunucu
doğrulaması, panelde giriş zorunluluğu, tüm panel sayfalarının açılması, fotoğraf yükleme/kapak/silme,
geçersiz dosya reddi, ayarlar ve **mağazalar arası yalıtım**. CI'da `manage.py check` ve `manage.py test`
çalıştırmanız yeterlidir; harici servis gerekmez.

Arayüz değişikliklerini tarayıcıda da kontrol edin: özellikle 360–420 px genişlikte (müşteriler telefonla gelir).

## Yayına alma

Genel çerçeve (CI/CD sizde olduğu için yalnızca gereksinimler):

1. Ortam değişkenlerini ayarlayın (yukarıdaki tablo). `DJANGO_SECRET_KEY` ve `SITE_URL` zorunludur.
2. `pip install -r requirements.txt gunicorn` (+ PostgreSQL kullanıyorsanız `psycopg[binary]`).
3. `python manage.py migrate` ve `python manage.py collectstatic --noinput`.
4. `gunicorn config.wsgi` bir ters vekilin (nginx vb.) arkasında çalışsın; TLS vekilde sonlansın ve
   `X-Forwarded-Proto` başlığını iletsin (ayarlar `DEBUG=0` iken bu başlığa güvenir).
5. **`static/` (`STATIC_ROOT`) ve `media/` (`MEDIA_ROOT`) klasörlerini web sunucusundan sunun.** `DEBUG=0`
   iken Django bu dosyaları kendisi sunmaz; sunulmazsa ürün fotoğrafları ve CSS görünmez.
6. `media/` kalıcı diskte olmalı ve yedeklenmelidir (ürün fotoğrafları yalnızca burada).
7. Platform yöneticisi için `createsuperuser`. `demo_yukle`'yi çalıştırmayın.

Üretimde nginx'in `client_max_body_size` değeri, bir seferde yüklenecek çoklu fotoğrafı kaldıracak kadar
(örn. `50m`) olmalıdır.

**QR kodlar basılmadan önce alan adı kesinleşmelidir.** Kod `<SITE_URL>/q/<kod>/` adresini taşır; alan adı
değişirse basılı kodlar çalışmaz (adres yönlendirmesi ile kurtarılabilir ama planlayın).

## Güvenlik ve gizlilik notları

- CSRF koruması tüm POST formlarında açıktır. Panel çıkışı POST'tur.
- Panelde tüm veri erişimi mağaza süzgeçlidir (bkz. kiracı yalıtımı). Yüklenen dosyalar WebP'ye yeniden
  kodlanır; kullanıcıdan gelen dosya olduğu gibi saklanmaz.
- Tarayıcıdan gelen özel dikim ölçüleri ve renk seçimleri sunucuda yeniden doğrulanır; başka mağazanın
  rengi kabul edilmez.
- Yönlendirme parametreleri (`next`) `url_has_allowed_host_and_scheme` ile doğrulanır.
- Panel sayfaları `noindex` etiketlidir.
- **Kişisel veri:** özel dikim talep formu **ad ve telefon** toplar ve veritabanında saklar. Yayına almadan
  önce bir aydınlatma metni (KVKK) ve saklama/silme politikası eklenmelidir. Esnaf talepleri panelden silebilir.
- Giriş denemesi sınırlaması yoktur; internete açık yayında `django-axes` gibi bir çözüm ya da vekil
  katmanında hız sınırı eklenmelidir.

## Bilinen eksikler ve fikirler

- Esnafın kendi kendine kayıt olması ve paket/abonelik yönetimi yok; mağazaları platform sahibi açar.
- Şifre sıfırlama e-postası yok (e-posta altyapısı kurulmadı); şifreyi platform sahibi admin'den sıfırlar.
- Toplu ürün yükleme (Excel/CSV) yok.
- Mağaza başına özel alan adı yok.
- Arama `contains` tabanlıdır (bkz. Türkçe arama); büyük kataloglarda tam metin aramaya geçilmeli.
- Çizimler şematiktir, fotoğraf gerçekliğinde değildir; kumaş/fiyat formülleri kabadır.
- Satın alma yok. Eklenecekse ödeme sağlayıcısı, sipariş modeli ve stok takibi gerekir.
- Fikirler: favori listesi, ürün başına paylaşım önizlemesi (OG görseli), çok dilli arayüz, okutma/görüntüleme
  istatistiklerinin zaman grafiği.

## Yeni esnafı sisteme alma

1. `/admin/` → **Kullanıcılar** → kullanıcı oluşturun (personel/süper kullanıcı **işaretlemeyin**).
2. `/admin/` → **Mağazalar** → mağaza ekleyin; alttaki "Mağaza yetkilileri" satırında o kullanıcıyı seçin.
3. Esnafa `/panel/` adresini, kullanıcı adını ve şifresini verin. Gerisini (ürünler, fotoğraflar, renkler, numara,
   tema, QR afişi) panelden kendisi yapar.

Bir mağazaya birden çok kullanıcı, bir kullanıcıya birden çok mağaza (şube) bağlanabilir; birden çok
mağazası olan kullanıcı panelin alt kısmındaki seçiciyle mağaza değiştirir.

## Git akışı

- Ana dal `main`. Uzak depo: `https://github.com/suedatgrl/Catalog.git`.
- Commit'lemeden önce `manage.py test` geçmeli; model değişikliklerinde migration dosyası commit'e girmeli.
