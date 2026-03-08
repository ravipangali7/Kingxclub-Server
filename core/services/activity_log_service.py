"""Create ActivityLog entries for login, deposit, withdraw, password change, profile update, etc."""
from django.utils import timezone

from core.models import ActivityLog


def create_activity_log(user, action, request=None, game=None, remarks=""):
    """Create a single activity log entry. request is optional (for IP and device)."""
    now = timezone.now()
    ip = None
    device = ""
    if request:
        ip = request.META.get("REMOTE_ADDR")
        ua = request.META.get("HTTP_USER_AGENT") or ""
        device = ua[:255]
    ActivityLog.objects.create(
        user=user,
        action=action,
        game=game,
        remarks=(remarks[:500] if remarks else ""),
        action_date=now.date(),
        action_time=now.time(),
        ip=ip,
        device=device,
    )
