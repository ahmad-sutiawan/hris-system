from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.employees.serializers import EmployeeSelfSerializer, EmployeeSerializer


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [AuthRateThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthRateThrottle]


class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = getattr(user, "employee_profile", None)
        if profile and (user.is_hr or user.is_admin):
            employee_data = EmployeeSerializer(profile).data
        elif profile:
            employee_data = EmployeeSelfSerializer(profile).data
        else:
            employee_data = None
        payload = {
            "id": user.pk,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "plant_id": user.plant_id,
            "employee": employee_data,
        }
        return Response(payload)
