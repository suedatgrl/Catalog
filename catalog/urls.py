from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("q/<str:code>/", views.qr_redirect, name="qr"),
    path("<slug:slug>/", views.shop_home, name="shop"),
    path("<slug:slug>/ozel-dikim/", views.custom_design, name="custom"),
    path("<slug:slug>/urun/<slug:product_slug>/", views.product_detail, name="product"),
]
