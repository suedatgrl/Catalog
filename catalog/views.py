import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .kinds import kind_config
from .models import CustomRequest, Product, Shop
from .utils import normalize

PAGE_SIZE = 24


def landing(request):
    return render(request, "store/landing.html")


def qr_redirect(request, code):
    """QR kodlar buraya gelir: okutmayı sayar, mağazaya yönlendirir.
    Mağaza adresi (slug) değişse bile basılı QR kodlar çalışmaya devam eder."""
    shop = get_object_or_404(Shop, qr_code=code, is_active=True)
    Shop.objects.filter(pk=shop.pk).update(scan_count=F("scan_count") + 1)
    target = shop.get_absolute_url()
    product_id = request.GET.get("u", "")
    if product_id.isdigit():
        product = shop.products.filter(pk=product_id, is_active=True).first()
        if product:
            target = product.get_absolute_url()
    return redirect(target)


def _shop(slug):
    return get_object_or_404(Shop, slug=slug, is_active=True)


def _has_custom(shop):
    return shop.custom_enabled and shop.custom_items.filter(is_active=True).exists()


def shop_home(request, slug):
    shop = _shop(slug)
    products = (
        shop.products.filter(is_active=True).select_related("shop").prefetch_related("images")
    )

    q = request.GET.get("q", "").strip()[:60]
    category_slug = request.GET.get("kategori", "")
    category = None
    for word in normalize(q).split():
        products = products.filter(search_text__contains=word)
    if category_slug:
        category = shop.categories.filter(slug=category_slug).first()
        if category:
            products = products.filter(category=category)

    page = Paginator(products, PAGE_SIZE).get_page(request.GET.get("sayfa"))

    if request.headers.get("X-Requested-With") == "fetch":
        return render(request, "store/_cards.html", {"shop": shop, "products": page})

    filtered = bool(q or category)
    context = {
        "shop": shop,
        "products": page,
        "categories": shop.categories.filter(products__is_active=True).distinct(),
        "q": q,
        "category": category,
        "filtered": filtered,
        "has_custom": _has_custom(shop),
    }
    return render(request, "store/home.html", context)


def product_detail(request, slug, product_slug):
    shop = _shop(slug)
    product = get_object_or_404(
        shop.products.select_related("category"), slug=product_slug, is_active=True
    )
    Product.objects.filter(pk=product.pk).update(view_count=F("view_count") + 1)

    related = shop.products.filter(is_active=True).exclude(pk=product.pk)
    if product.category_id:
        related = related.filter(category_id=product.category_id)
    context = {
        "shop": shop,
        "product": product,
        "images": list(product.images.all()),
        "related": related.select_related("shop").prefetch_related("images")[:6],
        "page_url": request.build_absolute_uri(),
        "has_custom": _has_custom(shop),
    }
    return render(request, "store/product.html", context)


@require_http_methods(["GET", "POST"])
def custom_design(request, slug):
    shop = _shop(slug)
    if not shop.custom_enabled:
        raise Http404
    items = list(shop.custom_items.filter(is_active=True))
    colors = list(shop.fabric_colors.all())
    if not items or not colors:
        raise Http404

    if request.method == "POST":
        return _save_request(request, shop, items, colors)

    config = {
        "items": [
            {
                "id": it.pk,
                "name": it.name,
                "desc": it.description,
                "base": float(it.base_price or 0),
                "m2": float(it.price_per_m2) if it.price_per_m2 else None,
                **kind_config(it.kind),
            }
            for it in items
        ],
        "colors": [
            {
                "id": c.pk,
                "name": c.name,
                "hex": c.hex,
                "hex2": c.hex2,
                "pattern": c.pattern,
                "image": c.image.url if c.image else "",
            }
            for c in colors
        ],
        "shop": shop.name,
        "wa": shop.wa_number,
    }
    return render(
        request,
        "store/custom.html",
        {"shop": shop, "config": config, "has_custom": True, "sent": request.GET.get("ok") == "1"},
    )


def _save_request(request, shop, items, colors):
    """Talebi kaydeder. Tarayıcıdan gelen her değer sunucuda yeniden doğrulanır."""
    back = redirect("catalog:custom", slug=shop.slug)
    if request.POST.get("website"):  # bot tuzağı: gerçek kullanıcı bu alanı görmez
        return back

    item = next((i for i in items if str(i.pk) == request.POST.get("item")), None)
    name = request.POST.get("customer_name", "").strip()[:80]
    phone = request.POST.get("phone", "").strip()[:20]
    if not item or not name or sum(ch.isdigit() for ch in phone) < 10:
        messages.error(request, "Lütfen adınızı ve geçerli bir telefon numarası yazın.")
        return back

    try:
        raw_dims = json.loads(request.POST.get("dims", "{}"))
        raw_parts = json.loads(request.POST.get("parts", "{}"))
        if not isinstance(raw_dims, dict) or not isinstance(raw_parts, dict):
            raise ValueError
    except ValueError:
        messages.error(request, "Ölçüler okunamadı, lütfen tekrar deneyin.")
        return back

    info = item.kind_info
    dims = {}
    for key, label, lo, hi, default in info["dims"]:
        try:
            value = int(float(raw_dims.get(key, default)))
        except (TypeError, ValueError):
            value = default
        dims[label] = max(lo, min(hi, value))

    color_names = {str(c.pk): c.name for c in colors}
    chosen = {
        label: color_names[str(raw_parts.get(key))]
        for key, label in info["parts"]
        if str(raw_parts.get(key)) in color_names
    }

    CustomRequest.objects.create(
        shop=shop,
        item=item,
        item_name=item.name,
        dims=dims,
        colors=chosen,
        customer_name=name,
        phone=phone,
        note=request.POST.get("note", "").strip()[:300],
    )
    return redirect(f"{back.url}?ok=1")
