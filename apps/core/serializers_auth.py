from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class HRISTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login: NIK + Employee ID (password) via HRISAuthenticationBackend."""

    def validate(self, attrs):
        username = attrs.get(self.username_field)
        password = attrs.get("password")
        request = self.context.get("request")

        user = authenticate(
            request=request,
            username=username,
            password=password,
        )
        if user is None or not user.is_active:
            raise serializers.ValidationError(
                "Tidak ada akun aktif yang ditemukan dengan kredensial yang diberikan",
                code="authorization",
            )

        refresh = self.get_token(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
