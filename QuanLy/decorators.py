# QuanLy/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.conf import settings
from django.core.exceptions import PermissionDenied


def group_required(*group_names):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            # Nếu chưa login → về đúng LOGIN_URL
            if not user.is_authenticated:
                return redirect(settings.LOGIN_URL)

            # SUPERUSER luôn vào được
            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Nếu không yêu cầu group, cho luôn
            if not group_names:
                return view_func(request, *args, **kwargs)

            # Nếu user thuộc ít nhất một group
            if user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)

            # Không đủ quyền → 403
            raise PermissionDenied

        return _wrapped_view

    return decorator
# QuanLy/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.conf import settings
from django.core.exceptions import PermissionDenied





def get_permission_flags(user):

    is_manager = False      # Cửa hàng trưởng
    is_employee = False     # Nhân viên
    is_supplier = False     # Nhà cung ứng

    if user.is_authenticated:
        groups = set(user.groups.values_list("name", flat=True))
        is_manager = "Cửa hàng trưởng" in groups
        is_employee = "Nhân viên" in groups
        is_supplier = "Nhà cung ứng" in groups

    return {
        "is_manager": is_manager,
        "is_employee": is_employee,
        "is_supplier": is_supplier,

        # --- Nhà cung ứng ---
        # add_supplier & edit_supplier đang dùng group_required('Cửa hàng trưởng', 'Nhà cung ứng')
        "can_add_supplier": is_manager ,
        "can_edit_supplier": is_manager or is_supplier,

        # --- Đơn đặt hàng (PO) ---
        # create_po: Cửa hàng trưởng + Nhân viên
        "can_create_po": is_manager or is_employee,
        # po_edit: chỉ Cửa hàng trưởng (xem trong views.py)
        "can_edit_po": is_manager,
        # po_list: Cửa hàng trưởng + Nhân viên + Nhà cung ứng
        "can_view_po": is_manager or is_employee or is_supplier,

        # ASN permissions
        "can_view_asn": True,  # tất cả đều xem được
        "can_create_asn": is_supplier,  # chỉ Nhà cung ứng
        "can_edit_asn": is_supplier,

    }
