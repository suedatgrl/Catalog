# Vitrin — QR ile açılan dijital katalog

Esnaf ve işletmeler için çok mağazalı ürün kataloğu. Müşteri dükkândaki QR kodu okutur,
ürünleri telefonunda görür. Mağaza sahibi ürünlerini kod yazmadan kendi panelinden yönetir.

## Yerelde çalıştırma

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser   # platform yöneticisi (siz)
.venv/bin/python manage.py demo_yukle        # isteğe bağlı örnek mağaza (demo / demo12345)
.venv/bin/python manage.py runserver 0.0.0.0:8000
.venv/bin/python manage.py test
```

| Adres | Kim kullanır |
|---|---|
| `/<magaza-adresi>/` | Müşteri: katalog, arama, ürün sayfası |
| `/<magaza-adresi>/ozel-dikim/` | Müşteri: ölçü + renk ile özel dikim önizlemesi, teklif talebi |
| `/q/<kod>/` | QR kodların gittiği adres (okutmayı sayar, mağazaya yönlendirir) |
| `/panel/` | Esnaf: ürün, kategori, renk kartelası, talepler, QR, ayarlar |
| `/admin/` | Platform sahibi: mağaza açma, kullanıcı tanımlama |

## Yeni bir esnafı sisteme alma

1. `/admin/` → **Kullanıcılar** → kullanıcı oluşturun (personel/süper kullanıcı işaretlemeyin).
2. `/admin/` → **Mağazalar** → mağaza ekleyin, alttaki “Mağaza yetkilileri” satırında o kullanıcıyı seçin.
3. Esnafa `/panel/` adresini, kullanıcı adını ve şifresini verin. Gerisini panelden kendisi yapar.

Bir mağazaya birden çok kullanıcı, bir kullanıcıya birden çok mağaza (şube) bağlanabilir.

## Yapı

- `catalog/` — veri modelleri, müşteri sayfaları, `kinds.py` (özel dikim türleri ve ölçü sınırları)
- `panel/` — esnaf paneli; her sorgu `request.shop` ile o mağazayla sınırlıdır
- `static/js/visualizer.js` — özel dikim çizimleri (SVG) ve tahmini kumaş hesabı
- `templates/store/`, `templates/panel/` — arayüz

## Yayına alırken

Ortam değişkenleri: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CSRF_TRUSTED_ORIGINS`, `SITE_URL` (QR kodlara yazılan kök adres), isteğe bağlı
`DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT` (PostgreSQL), `MEDIA_ROOT`, `PLATFORM_NAME`.

- `collectstatic` çalıştırın; `static/` ve `media/` klasörlerini web sunucusundan (nginx vb.) sunun.
  Django `DEBUG=0` iken bu dosyaları kendisi sunmaz.
- `media/` kalıcı diskte olmalı ve yedeklenmeli (ürün fotoğrafları burada).
- **`SITE_URL`'yi QR kodları basmadan önce kesinleştirin.** Alan adı değişirse basılı kodlar çalışmaz.
