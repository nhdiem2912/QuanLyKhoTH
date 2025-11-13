from django import template

register = template.Library()

@register.filter
def total_discount(items):
    """
    Tính tổng chiết khấu (VNĐ) từ danh sách items.
    Mỗi item phải có property discount_value trong model.
    """
    total = 0
    try:
        for item in items:
            total += getattr(item, "discount_value", 0)
    except Exception:
        total = 0
    return total
from django import template

register = template.Library()

@register.filter
def sum(items, field_name):
    """Tính tổng 1 field trong queryset (vd: sum quantity)."""
    return sum(getattr(i, field_name, 0) for i in items)

@register.filter
def sum_price(items):
    """Tính tổng tiền = tổng field total."""
    return sum(i.total for i in items if hasattr(i, "total"))
from django import template

register = template.Library()

@register.filter
def sum(items, field_name):
    """Tính tổng 1 trường trong queryset."""
    try:
        return sum(getattr(i, field_name, 0) for i in items)
    except Exception:
        return 0

@register.filter
def sum_price(items):
    """Tính tổng tiền."""
    try:
        return sum((getattr(i, "total", 0) or 0) for i in items)
    except:
        return 0
from django import template

register = template.Library()

@register.filter
def total_discount(items):
    """
    Tính tổng tiền chiết khấu của toàn bộ items của ImportReceipt.
    items phải là queryset: receipt.items.all()
    """
    total = 0
    for item in items:
        base = item.quantity * item.unit_price
        discount_amount = base * (item.discount_percent / 100)
        total += discount_amount
    return total
