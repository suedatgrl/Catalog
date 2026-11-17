from decimal import Decimal
from urllib.parse import quote

from django import template

register = template.Library()


@register.filter
def tl(value):
    """1299.9 -> '1.299,90 ₺'  (kuruş yoksa '1.299 ₺')"""
    if value is None or value == "":
        return ""
    value = Decimal(value).quantize(Decimal("0.01"))
    whole, _, frac = f"{value:,.2f}".partition(".")
    whole = whole.replace(",", ".")
    return f"{whole} ₺" if frac == "00" else f"{whole},{frac} ₺"


@register.simple_tag
def wa_link(number, text=""):
    """WhatsApp sohbet bağlantısı (hazır mesajla)."""
    if not number:
        return ""
    return f"https://wa.me/{number}" + (f"?text={quote(text)}" if text else "")


@register.filter
def initial(value):
    return str(value)[:1].upper() if value else "?"
