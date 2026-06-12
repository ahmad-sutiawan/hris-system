from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        payload = {"status": "ok", "service": "hris-lite", "version": "1.0.0", "database": "ok"}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as exc:
            payload["status"] = "degraded"
            payload["database"] = str(exc)
            return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(payload)
