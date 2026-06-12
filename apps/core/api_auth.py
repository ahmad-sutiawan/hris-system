from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.employees.serializers import EmployeeSerializer


class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = getattr(user, "employee_profile", None)
        payload = {
            "id": user.pk,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "plant_id": user.plant_id,
            "employee": EmployeeSerializer(profile).data if profile else None,
        }
        return Response(payload)
