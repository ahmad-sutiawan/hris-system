from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy

from apps.web.forms import HRISLoginForm
from apps.employees.services.user_link import ensure_employee_profile


class HRISLoginView(LoginView):
    template_name = "web/login.html"
    form_class = HRISLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("web:dashboard")

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_superuser and not user.tenant_id:
            messages.error(
                self.request,
                "Akun belum terhubung ke tenant. Hubungi administrator HRIS.",
            )
            return self.form_invalid(form)

        remember = form.cleaned_data.get("remember_me")
        if remember:
            self.request.session.set_expiry(60 * 60 * 24 * 14)
        else:
            self.request.session.set_expiry(0)

        response = super().form_valid(form)
        display_name = user.get_full_name() or user.username
        messages.success(self.request, f"Selamat datang, {display_name}.")
        if user.role in {user.Role.EMPLOYEE, user.Role.MANAGER}:
            ensure_employee_profile(user)
        return response


class HRISLogoutView(LogoutView):
    next_page = reverse_lazy("web:login")
    http_method_names = ["get", "post", "head", "options"]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.method == "POST":
            messages.success(request, "Anda berhasil keluar. Sampai jumpa!")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("web:dashboard")
        return redirect(self.next_page)
