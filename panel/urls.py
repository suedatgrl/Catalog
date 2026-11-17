from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "panel"

urlpatterns = [
    path("giris/", auth_views.LoginView.as_view(template_name="panel/login.html", redirect_authenticated_user=True), name="login"),
    path("cikis/", auth_views.LogoutView.as_view(), name="logout"),
    path("sifre/", views.panel_view(views.PasswordView.as_view(success_url=reverse_lazy("panel:dashboard"))), name="password"),
    path("", views.dashboard, name="dashboard"),
    path("magaza-sec/", views.switch_shop, name="switch"),
    path("urunler/", views.product_list, name="products"),
    path("urunler/yeni/", views.product_edit, name="product_new"),
    path("urunler/<int:pk>/", views.product_edit, name="product_edit"),
    path("urunler/<int:pk>/sil/", views.product_delete, name="product_delete"),
    path("urunler/<int:pk>/durum/", views.product_toggle, name="product_toggle"),
    path("gorsel/<int:pk>/sil/", views.image_delete, name="image_delete"),
    path("gorsel/<int:pk>/kapak/", views.image_cover, name="image_cover"),
    path("kategoriler/", views.categories, name="categories"),
    path("renkler/", views.colors, name="colors"),
    path("ozel-dikim/", views.custom_items, name="custom_items"),
    path("<str:kind>/<int:pk>/duzenle/", views.simple_edit, name="edit"),
    path("<str:kind>/<int:pk>/sil/", views.simple_delete, name="delete"),
    path("talepler/", views.requests_list, name="requests"),
    path("talepler/<int:pk>/durum/", views.request_status, name="request_status"),
    path("ayarlar/", views.shop_settings, name="settings"),
    path("qr/", views.qr_page, name="qr"),
    path("qr/afis/", views.qr_poster, name="qr_poster"),
    path("qr/kod.<str:fmt>", views.qr_image, name="qr_image"),
]
