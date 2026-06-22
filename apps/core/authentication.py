from django.contrib.auth.backends import ModelBackend
import logging

from apps.core.auth_login import resolve_user_for_login

logger = logging.getLogger(__name__)


class HRISAuthenticationBackend(ModelBackend):
    """Auth backend: karyawan login NIK / Employee ID; admin pakai username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            user = resolve_user_for_login(username, employee_id_hint=password)
        except Exception:
            logger.exception("Gagal resolve user untuk login identifier=%r", username)
            return None
        if user is None:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        return super().get_user(user_id)
