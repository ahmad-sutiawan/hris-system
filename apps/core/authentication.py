from django.contrib.auth.backends import ModelBackend

from apps.core.auth_login import resolve_user_for_login


class HRISAuthenticationBackend(ModelBackend):
    """Auth backend: karyawan login NIK / Employee ID; admin pakai username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        user = resolve_user_for_login(username, employee_id_hint=password)
        if user is None:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        return super().get_user(user_id)
