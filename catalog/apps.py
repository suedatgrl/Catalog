from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalog'

    def ready(self):
        from . import security  # noqa: F401  (giriş hız sınırı sinyallerini kaydeder)
