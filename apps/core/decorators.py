from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def require_roles(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("web:login")
            if request.user.is_admin or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "Anda tidak memiliki akses ke halaman ini.")
            return redirect("web:dashboard")

        return wrapper

    return decorator


def require_admin(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("web:login")
        if not (request.user.is_admin or request.user.is_superuser):
            messages.error(request, "Halaman ini hanya untuk Admin / Superuser.")
            return redirect("web:dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper


def user_has_admin_console(user) -> bool:
    return bool(user.is_authenticated and (user.is_admin or user.is_superuser))


def user_can_manage_master_data(user) -> bool:
    return bool(user.is_authenticated and (user.is_admin or user.is_hr or user.is_superuser))


def require_master_data(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("web:login")
        if not user_can_manage_master_data(request.user):
            messages.error(request, "Halaman Master Data hanya untuk Admin / HR.")
            return redirect("web:dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper
