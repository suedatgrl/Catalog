"""Güvenlik katmanı: yanıt başlıkları (CSP), istek boyutu sınırı, giriş hız sınırı.

Sayaçlar Django önbelleğinde tutulur. Varsayılan LocMem önbellek süreç başınadır:
birden çok gunicorn işçisi varsa sınır işçi sayısı kadar gevşer. Çoklu işçide
CACHES'i Redis/Memcached/veritabanı önbelleğine çevirin.
"""
import hashlib

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core.cache import cache
from django.dispatch import receiver
from django.http import HttpResponse
from django.urls import reverse

from .utils import client_ip, hit

# Betikler yalnızca kendi alan adımızdan çalışır; satır içi <script> ve onclick="" yoktur.
# Stil için 'unsafe-inline' gerekir (şablonlarda style="" öznitelikleri var); bu betik
# çalıştırmaz. Yazı tipi Google Fonts'tan gelir.
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])
PERMISSIONS = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"

LOGIN_WINDOW = 15 * 60   # saniye
USER_LIMIT = 5           # aynı IP + aynı kullanıcı adı için art arda hatalı deneme
IP_LIMIT = 20            # aynı IP, hangi kullanıcı adı olursa olsun


def _login_paths():
    return {reverse("panel:login"), "/" + settings.ADMIN_URL + "login/"}


def _user_key(ip, username):
    digest = hashlib.sha256(username.strip().lower().encode()).hexdigest()[:24]
    return f"login-user:{ip}:{digest}"


class HardeningMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self._blocked(request) or self.get_response(request)
        self._add_headers(request, response)
        return response

    def _blocked(self, request):
        if request.method != "POST":
            return None
        try:
            length = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        if length > settings.MAX_REQUEST_MB * 1024 * 1024:
            return HttpResponse("İstek çok büyük.", status=413, content_type="text/plain; charset=utf-8")
        if request.path in _login_paths():
            ip = client_ip(request)
            username = request.POST.get("username", "")[:150]
            if cache.get(f"login-ip:{ip}", 0) >= IP_LIMIT or cache.get(_user_key(ip, username), 0) >= USER_LIMIT:
                response = HttpResponse(
                    "Çok fazla hatalı giriş denemesi. Lütfen 15 dakika sonra tekrar deneyin.",
                    status=429, content_type="text/plain; charset=utf-8",
                )
                response["Retry-After"] = str(LOGIN_WINDOW)
                return response
        return None

    def _add_headers(self, request, response):
        in_admin = request.path.startswith("/" + settings.ADMIN_URL)
        debug_error_page = settings.DEBUG and response.status_code >= 500  # teknik hata sayfası satır içi betik kullanır
        if not in_admin and not debug_error_page:
            response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("Permissions-Policy", PERMISSIONS)


@receiver(user_login_failed)
def _login_failed(sender, credentials, request=None, **kwargs):
    if request is None:
        return
    ip = client_ip(request)
    hit(f"login-ip:{ip}", LOGIN_WINDOW)
    hit(_user_key(ip, str(credentials.get("username", ""))[:150]), LOGIN_WINDOW)


@receiver(user_logged_in)
def _login_ok(sender, request=None, user=None, **kwargs):
    # Yalnızca IP+kullanıcı sayacı sıfırlanır; IP sayacı sıfırlanmaz ki saldırgan
    # kendi hesabıyla girerek sınırı sıfırlayamasın.
    if request is not None and user is not None:
        cache.delete(_user_key(client_ip(request), user.get_username()))
