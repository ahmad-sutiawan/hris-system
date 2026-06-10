from apps.core.models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notifications": 0, "recent_notifications": []}
    qs = Notification.objects.filter(user=request.user, is_read=False)
    return {
        "unread_notifications": qs.count(),
        "recent_notifications": Notification.objects.filter(user=request.user).order_by(
            "-created_at"
        )[:5],
    }
