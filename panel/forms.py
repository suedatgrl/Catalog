from django import forms
from django.conf import settings

from catalog.models import Category, CustomItem, FabricColor, Product, Shop
from catalog.utils import process_image


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        single = super().clean
        return [single(f, initial) for f in files]


class ShopFormMixin:
    """Formu mağazaya bağlar; yeni kayıtlar otomatik o mağazaya yazılır."""

    def __init__(self, *args, shop, **kwargs):
        super().__init__(*args, **kwargs)
        self.shop = shop
        if not self.instance.pk:
            self.instance.shop = shop


class ProductForm(ShopFormMixin, forms.ModelForm):
    new_images = MultipleImageField(
        label="Fotoğraf ekle",
        required=False,
        widget=MultipleFileInput(attrs={"accept": "image/*"}),
    )

    class Meta:
        model = Product
        fields = [
            "name", "category", "price", "old_price", "description", "sizes", "colors",
            "specs", "sku", "in_stock", "is_featured", "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "specs": forms.Textarea(attrs={"rows": 4, "placeholder": "Güç: 2400 W\nGaranti: 2 yıl"}),
            "price": forms.NumberInput(attrs={"inputmode": "decimal", "step": "0.01"}),
            "old_price": forms.NumberInput(attrs={"inputmode": "decimal", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = self.shop.categories.all()
        self.fields["category"].empty_label = "Kategorisiz"

    def clean_new_images(self):
        files = self.cleaned_data.get("new_images") or []
        limit = settings.MAX_IMAGE_MB * 1024 * 1024
        for f in files:
            if f.size > limit:
                raise forms.ValidationError(
                    f"“{f.name}” çok büyük. En fazla {settings.MAX_IMAGE_MB} MB yükleyebilirsiniz."
                )
        existing = self.instance.images.count() if self.instance.pk else 0
        if existing + len(files) > settings.MAX_IMAGES_PER_PRODUCT:
            raise forms.ValidationError(
                f"Bir ürüne en fazla {settings.MAX_IMAGES_PER_PRODUCT} fotoğraf eklenebilir."
            )
        return files


class CategoryForm(ShopFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "order"]


class FabricColorForm(ShopFormMixin, forms.ModelForm):
    class Meta:
        model = FabricColor
        fields = ["name", "hex", "pattern", "hex2", "image", "order"]
        widgets = {
            "hex": forms.TextInput(attrs={"type": "color"}),
            "hex2": forms.TextInput(attrs={"type": "color"}),
            "image": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def save(self, commit=True):
        obj = super().save(commit=False)
        if "image" in self.changed_data and self.cleaned_data.get("image"):
            obj.image = process_image(self.cleaned_data["image"], 500, quality=80)
        if commit:
            obj.save()
        return obj


class CustomItemForm(ShopFormMixin, forms.ModelForm):
    class Meta:
        model = CustomItem
        fields = ["kind", "name", "description", "base_price", "price_per_m2", "order", "is_active"]


class ShopSettingsForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = [
            "name", "tagline", "description", "logo", "theme", "phone", "whatsapp",
            "instagram", "address", "working_hours", "show_prices", "custom_enabled",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "theme": forms.RadioSelect,
            "logo": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def save(self, commit=True):
        obj = super().save(commit=False)
        if "logo" in self.changed_data and self.cleaned_data.get("logo"):
            obj.logo = process_image(self.cleaned_data["logo"], 400, keep_alpha=True)
        if commit:
            obj.save()
        return obj
