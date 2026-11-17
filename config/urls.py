from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = f"{settings.PLATFORM_NAME} — Platform Yönetimi"
admin.site.site_title = settings.PLATFORM_NAME

urlpatterns = [
    path("admin/", admin.site.urls),
    path("panel/", include("panel.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Mağaza adresleri kök dizinde (/magaza-adi/) olduğu için en sonda durmalı.
urlpatterns += [path("", include("catalog.urls"))]
