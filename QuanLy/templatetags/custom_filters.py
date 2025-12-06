from django import template
from django.forms.boundfield import BoundField

register = template.Library()
# 1) Tổng chiết khấu
@register.filter(name="total_discount")
def total_discount(items):
    total = 0
    try:
        for item in items:
            base = (item.quantity or 0) * (item.unit_price or 0)
            percent = getattr(item, "discount_percent", 0) or 0
            total += base * percent / 100
    except Exception:
        pass
    return total


# 2) Tổng theo một trường

@register.filter(name="sum_field")
def sum_field(items, field_name):
    try:
        return sum(getattr(i, field_name, 0) or 0 for i in items)
    except Exception:
        return 0


# 3) Tổng giá tiền (total)

@register.filter(name="sum_price")
def sum_price(items):
    try:
        return sum((getattr(i, "total", 0) or 0) for i in items)
    except Exception:
        return 0


# 4) Kiểm tra user có thuộc nhóm

@register.filter(name="has_any_group")
def has_any_group(user, group_names):

    if not getattr(user, "is_authenticated", False):
        return False

    names = [g.strip() for g in str(group_names).split(",") if g.strip()]
    if not names:
        return False

    return user.groups.filter(name__in=names).exists() or user.is_superuser


# 5) Thêm CSS class cho field
@register.filter(name="add_class")
def add_class(field, css):
    if not isinstance(field, BoundField):
        return field
    existing = field.field.widget.attrs.get("class", "")
    new_class = (existing + " " + css).strip()
    return field.as_widget(attrs={"class": new_class})



# 6) Thêm bất kỳ attribute
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

