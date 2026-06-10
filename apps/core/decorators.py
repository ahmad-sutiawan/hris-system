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
