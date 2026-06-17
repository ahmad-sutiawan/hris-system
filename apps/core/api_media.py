from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.media_serving import serve_protected_media


class MediaFileView(APIView):
    """Serve protected media through API (CORS + JWT) for mobile/web clients."""

    permission_classes = [IsAuthenticated]

    def get(self, request, path):
        return serve_protected_media(request, path)
