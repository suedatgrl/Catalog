"""
Vitrin — çok mağazalı dijital katalog platformu.

Üretim için ortam değişkenleri:
  DJANGO_SECRET_KEY, DJANGO_DEBUG=0, DJANGO_ALLOWED_HOSTS=ornek.com,www.ornek.com
  SITE_URL=https://ornek.com   (QR kodların içine yazılan adres)
  DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT  (verilirse PostgreSQL kullanılır)
"""
import mimetypes
import os
from pathlib import Path

# Eski Python sürümleri .webp türünü tanımıyor; geliştirme sunucusu doğru başlıkla sunsun.
mimetypes.add_type("image/webp", ".webp")

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default):
    return os.environ.get(name, str(int(default))).lower() in ("1", "true", "yes", "on")


# Güvenli varsayılan: DEBUG KAPALI. Geliştirmede manage.py otomatik açar (bkz. manage.py).
DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY ortam değişkeni üretimde zorunludur.")
    SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"]  # yerel ağdan telefonla test edebilmek için

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# QR kodlara yazılacak kök adres. Boşsa isteğin geldiği adres kullanılır.
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
PLATFORM_NAME = os.environ.get("PLATFORM_NAME", "Vitrin")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "catalog",
    "panel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "catalog.security.HardeningMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "catalog.context.platform",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if os.environ.get("DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DB_NAME"],
            "USER": os.environ.get("DB_USER", ""),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "panel:login"
LOGIN_REDIRECT_URL = "panel:dashboard"
LOGOUT_REDIRECT_URL = "panel:login"

# Yüklenen ürün görseli başına üst sınır (MB) ve ürün başına görsel sayısı
MAX_IMAGE_MB = 12
MAX_IMAGE_PIXELS = 80_000_000  # ~80 MP; üstü reddedilir (bellek tüketme saldırısı)
MAX_REQUEST_MB = 100  # tek bir POST isteğinin üst sınırı (nginx client_max_body_size ile uyumlu olmalı)
MAX_IMAGES_PER_PRODUCT = 8

# Yönetim paneli adresi. Varsayılan "admin"; tahmin edilmesin diye üretimde değiştirin.
ADMIN_URL = os.environ.get("ADMIN_URL", "admin").strip("/") + "/"

# Uygulama bir ters vekil (nginx vb.) arkasındaysa True olmalı: HTTPS ve istemci IP'si
# vekilin ilettiği başlıklardan okunur. Vekil YOKSA False yapın, yoksa başlıklar sahtelenebilir.
BEHIND_PROXY = env_bool("BEHIND_PROXY", not DEBUG)

# Hız sınırı sayaçları burada tutulur (bkz. catalog/security.py).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

CSRF_COOKIE_HTTPONLY = True  # çerezi JS okumaz; formlar {% csrf_token %} kullanır
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

if not DEBUG:
    if not ALLOWED_HOSTS:
        raise RuntimeError("DJANGO_ALLOWED_HOSTS ortam değişkeni üretimde zorunludur (örn. ornek.com).")
    if BEHIND_PROXY:
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    # Vekil zaten HTTPS'e yönlendiriyorsa SECURE_SSL_REDIRECT=0 verin (yönlendirme döngüsünü önler).
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    # HSTS kısa başlar (1 saat). HTTPS'in sorunsuz çalıştığını gördükten sonra 31536000'e çıkarın.
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
