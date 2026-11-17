"""Esnaf paneli. Her sorgu request.shop ile sınırlandırılır; bir mağaza diğerinin verisini göremez."""
from functools import wraps
from io import BytesIO

import segno
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.core.paginator import Paginator
from django.db.models import Count, F, Max, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalog.models import (
    Category, CustomItem, CustomRequest, FabricColor, Product, ProductImage, Shop,
)
from catalog.utils import normalize, process_image, site_url

from .forms import CategoryForm, CustomItemForm, FabricColorForm, ProductForm, ShopSettingsForm


def user_shops(user):
    if user.is_superuser:
        return Shop.objects.all()
    return Shop.objects.filter(members__user=user, is_active=True)


def panel_view(view):
    """Giriş ister ve kullanıcının aktif mağazasını request.shop olarak bağlar."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        shops = user_shops(request.user)
        shop = shops.filter(pk=request.session.get("shop_id") or 0).first() or shops.first()
        if shop is None:
            return render(request, "panel/no_shop.html", status=403)
        request.shop = shop
        request.shops = shops
        return view(request, *args, **kwargs)

    return login_required(wrapper)


class PasswordView(PasswordChangeView):
    template_name = "panel/password.html"

    def form_valid(self, form):
        messages.success(self.request, "Şifreniz değiştirildi.")
        return super().form_valid(form)


@require_POST
@panel_view
def switch_shop(request):
    shop = get_object_or_404(request.shops, pk=request.POST.get("shop") or 0)
    request.session["shop_id"] = shop.pk
    return redirect("panel:dashboard")


@panel_view
def dashboard(request):
    shop = request.shop
    products = shop.products.all()
    stats = products.aggregate(total=Count("id"), views=Sum("view_count"))
    context = {
        "total": stats["total"],
        "views": stats["views"] or 0,
        "active": products.filter(is_active=True).count(),
        "new_requests": shop.custom_requests.filter(status="yeni").count(),
        "top": products.filter(view_count__gt=0).order_by("-view_count").prefetch_related("images")[:5],
        "no_photo": products.filter(images__isnull=True, is_active=True).count(),
        "store_url": site_url(request) + shop.get_absolute_url(),
    }
    return render(request, "panel/dashboard.html", context)


# ---------- Ürünler ----------

@panel_view
def product_list(request):
    products = request.shop.products.select_related("category").prefetch_related("images")
    q = request.GET.get("q", "").strip()
    for word in normalize(q).split():
        products = products.filter(search_text__contains=word)
    cat = request.GET.get("kategori", "")
    if cat.isdigit():
        products = products.filter(category_id=cat)
    status = request.GET.get("durum", "")
    if status == "yayinda":
        products = products.filter(is_active=True)
    elif status == "gizli":
        products = products.filter(is_active=False)
    elif status == "tukendi":
        products = products.filter(in_stock=False)
    page = Paginator(products.order_by("-created_at"), 30).get_page(request.GET.get("sayfa"))
    return render(
        request,
        "panel/product_list.html",
        {"products": page, "q": q, "cat": cat, "status": status,
         "categories": request.shop.categories.all()},
    )


@panel_view
def product_edit(request, pk=None):
    shop = request.shop
    product = get_object_or_404(Product, pk=pk, shop=shop) if pk else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=product, shop=shop)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        start = (product.images.aggregate(m=Max("order"))["m"] or 0) + 1
        for i, upload in enumerate(form.cleaned_data["new_images"]):
            ProductImage.objects.create(
                product=product,
                image=process_image(upload, 1600),
                thumb=process_image(upload, 600, quality=78),
                order=start + i,
            )
        messages.success(request, f"“{product.name}” kaydedildi.")
        if "save_new" in request.POST:
            return redirect("panel:product_new")
        return redirect("panel:product_edit", pk=product.pk)
    context = {
        "form": form,
        "product": product,
        "images": product.images.all() if product else [],
        "has_categories": shop.categories.exists(),
    }
    return render(request, "panel/product_form.html", context)


@require_POST
@panel_view
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, shop=request.shop)
    name = product.name
    product.delete()
    messages.success(request, f"“{name}” silindi.")
    return redirect("panel:products")


@require_POST
@panel_view
def product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk, shop=request.shop)
    field = request.POST.get("field")
    if field in ("is_active", "in_stock", "is_featured"):
        setattr(product, field, not getattr(product, field))
        product.save(update_fields=[field, "updated_at"])
    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = "panel:products"
    return redirect(target)


@require_POST
@panel_view
def image_delete(request, pk):
    image = get_object_or_404(ProductImage, pk=pk, product__shop=request.shop)
    product_id = image.product_id
    image.delete()
    return redirect("panel:product_edit", pk=product_id)


@require_POST
@panel_view
def image_cover(request, pk):
    """Seçilen fotoğrafı kapak (ilk sıra) yapar."""
    image = get_object_or_404(ProductImage, pk=pk, product__shop=request.shop)
    image.product.images.exclude(pk=image.pk).update(order=F("order") + 1)
    image.order = 0
    image.save(update_fields=["order"])
    return redirect("panel:product_edit", pk=image.product_id)


# ---------- Kategori / renk / özel dikim: aynı kalıp ----------

SIMPLE = {
    "kategori": (Category, CategoryForm, "panel:categories", "Kategoriyi düzenle"),
    "renk": (FabricColor, FabricColorForm, "panel:colors", "Rengi düzenle"),
    "ozel": (CustomItem, CustomItemForm, "panel:custom_items", "Özel dikim ürününü düzenle"),
}


def _list_and_add(request, form_class, template, queryset, extra=None):
    form = form_class(request.POST or None, request.FILES or None, shop=request.shop)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"“{obj}” eklendi.")
        return redirect(request.path)
    return render(request, template, {"form": form, "objects": queryset, **(extra or {})})


@panel_view
def categories(request):
    qs = request.shop.categories.annotate(n=Count("products"))
    return _list_and_add(request, CategoryForm, "panel/categories.html", qs)


@panel_view
def colors(request):
    return _list_and_add(request, FabricColorForm, "panel/colors.html", request.shop.fabric_colors.all())


@panel_view
def custom_items(request):
    return _list_and_add(
        request, CustomItemForm, "panel/custom_items.html", request.shop.custom_items.all(),
        {"color_count": request.shop.fabric_colors.count()},
    )


def _simple(kind):
    if kind not in SIMPLE:
        raise Http404
    return SIMPLE[kind]


@panel_view
def simple_edit(request, kind, pk):
    model, form_class, back, title = _simple(kind)
    obj = get_object_or_404(model, pk=pk, shop=request.shop)
    form = form_class(request.POST or None, request.FILES or None, instance=obj, shop=request.shop)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Kaydedildi.")
        return redirect(back)
    return render(request, "panel/edit.html", {"form": form, "title": title, "back": reverse(back)})


@require_POST
@panel_view
def simple_delete(request, kind, pk):
    model, _, back, _ = _simple(kind)
    obj = get_object_or_404(model, pk=pk, shop=request.shop)
    name = str(obj)
    obj.delete()
    messages.success(request, f"“{name}” silindi.")
    return redirect(back)


# ---------- Talepler ----------

@panel_view
def requests_list(request):
    page = Paginator(request.shop.custom_requests.all(), 30).get_page(request.GET.get("sayfa"))
    return render(request, "panel/requests.html", {"requests": page, "statuses": CustomRequest.STATUSES})


@require_POST
@panel_view
def request_status(request, pk):
    obj = get_object_or_404(CustomRequest, pk=pk, shop=request.shop)
    if request.POST.get("action") == "delete":
        obj.delete()
    elif request.POST.get("status") in dict(CustomRequest.STATUSES):
        obj.status = request.POST["status"]
        obj.save(update_fields=["status"])
    return redirect("panel:requests")


# ---------- Ayarlar ve QR ----------

@panel_view
def shop_settings(request):
    form = ShopSettingsForm(request.POST or None, request.FILES or None, instance=request.shop)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Mağaza bilgileri güncellendi.")
        return redirect("panel:settings")
    return render(request, "panel/settings.html", {"form": form})


def _qr_target(request):
    """QR'ın gideceği adres ve dosya adı. ?u=<ürün id> verilirse ürün etiketi üretir."""
    shop = request.shop
    url = site_url(request) + reverse("catalog:qr", args=[shop.qr_code])
    name = shop.slug
    product_id = request.GET.get("u", "")
    if product_id.isdigit():
        product = get_object_or_404(Product, pk=product_id, shop=shop)
        url += f"?u={product.pk}"
        name = f"{shop.slug}-{product.slug}"
    return url, name


@panel_view
def qr_image(request, fmt):
    if fmt not in ("png", "svg"):
        raise Http404
    url, name = _qr_target(request)
    qr = segno.make(url, error="m")
    buf = BytesIO()
    if fmt == "png":
        qr.save(buf, kind="png", scale=20, border=3)
        content_type = "image/png"
    else:
        qr.save(buf, kind="svg", scale=10, border=3, xmldecl=False)
        content_type = "image/svg+xml"
    response = HttpResponse(buf.getvalue(), content_type=content_type)
    if request.GET.get("indir"):
        response["Content-Disposition"] = f'attachment; filename="qr-{name}.{fmt}"'
    return response


@panel_view
def qr_page(request):
    url, _ = _qr_target(request)
    product_id = request.GET.get("u", "")
    product = (
        request.shop.products.filter(pk=product_id).first() if product_id.isdigit() else None
    )
    return render(request, "panel/qr.html", {"qr_url": url, "product": product})


@panel_view
def qr_poster(request):
    return render(request, "panel/qr_poster.html")
