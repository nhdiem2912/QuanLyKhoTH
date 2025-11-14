from django import template

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Dùng trong template: {% if user|has_group:"Cửa hàng trưởng" %}
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=group_name).exists()

@register.filter(name='has_any_group')
def has_any_group(user, group_names):
    """
    Kiểm tra user có thuộc BẤT KỲ group nào trong danh sách hay không.
    group_names: chuỗi, ngăn cách bởi dấu phẩy.
    Ví dụ: {% if user|has_any_group:"Cửa hàng trưởng,Nhân viên" %}
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    names = [g.strip() for g in group_names.split(',') if g.strip()]
    return user.groups.filter(name__in=names).exists()
