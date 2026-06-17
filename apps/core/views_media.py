from django.views import View

from apps.core.media_serving import serve_protected_media


class ProtectedMediaView(View):
    def get(self, request, path):
        return serve_protected_media(request, path)
