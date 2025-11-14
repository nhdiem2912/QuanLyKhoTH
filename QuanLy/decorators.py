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

            # ❗ Nếu chưa login → về đúng LOGIN_URL
            if not user.is_authenticated:
                return redirect(settings.LOGIN_URL)

            # ❗ SUPERUSER luôn vào được
            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            # ❗ Nếu không yêu cầu group, cho luôn
            if not group_names:
                return view_func(request, *args, **kwargs)

            # ❗ Nếu user thuộc ít nhất một group
            if user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)

            # ❗ Không đủ quyền → 403
            raise PermissionDenied

        return _wrapped_view

    return decorator
