"""Platform sahibinin (sizin) yönetim ekranı. Esnaflar burayı değil /panel/ adresini kullanır."""
from django.contrib import admin

from .models import Category, CustomItem, CustomRequest, FabricColor, Product, Shop, ShopMember


class ShopMemberInline(admin.TabularInline):
    model = ShopMember
    extra = 1
    autocomplete_fields = ["user"]


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "scan_count", "product_count", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = ["qr_code", "scan_count"]
    inlines = [ShopMemberInline]

    @admin.display(description="Ürün")
    def product_count(self, obj):
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "shop", "category", "price", "is_active"]
    list_filter = ["shop", "is_active"]
    search_fields = ["name", "sku"]
    exclude = ["slug"]


admin.site.register(Category, list_display=["name", "shop", "order"], list_filter=["shop"], exclude=["slug"])
admin.site.register(FabricColor, list_display=["name", "shop", "hex", "pattern"], list_filter=["shop"])
admin.site.register(CustomItem, list_display=["name", "shop", "kind", "is_active"], list_filter=["shop"])
admin.site.register(
    CustomRequest,
    list_display=["customer_name", "shop", "item_name", "status", "created_at"],
    list_filter=["shop", "status"],
)
