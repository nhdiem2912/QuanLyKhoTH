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
from django import template

register = template.Library()

@register.filter(name="has_any_group")
def has_any_group(user, group_names):
    """
    Trả về True nếu user thuộc ÍT NHẤT MỘT nhóm trong danh sách group_names
    group_names: chuỗi, ngăn cách bởi dấu phẩy, vd: "Cửa hàng trưởng,Nhân viên"
    """
    if not getattr(user, "is_authenticated", False):
        return False

    names = [g.strip() for g in str(group_names).split(",") if g.strip()]
    if not names:
        return False

    return user.groups.filter(name__in=names).exists() or user.is_superuser


# -------------------------------------------------
# 2) Thêm class CSS cho field form
#    {{ field|add_class:"form-control my-2" }}
# -------------------------------------------------
from django.forms.boundfield import BoundField

@register.filter(name="add_class")
def add_class(field, css):
    if not isinstance(field, BoundField):
        return field  # trả lại nguyên, không sửa
    existing = field.field.widget.attrs.get("class", "")
    new_class = (existing + " " + css).strip()
    return field.as_widget(attrs={"class": new_class})


@register.filter(name="attr")
def attr(field, arg):
    if not isinstance(field, BoundField):
        return field
    try:
        key, val = arg.split(":", 1)
    except ValueError:
        return field
    attrs = field.field.widget.attrs.copy()
    attrs[key] = val
    return field.as_widget(attrs=attrs)
