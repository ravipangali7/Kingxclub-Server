"""
Send OTP and other transactional email via Django's email backend.
Credentials and backend are configured in settings (env: EMAIL_HOST, EMAIL_HOST_USER, etc.).
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, otp: str) -> tuple[bool, str]:
    """
    Send OTP message to the given email (e.g. password reset).
    to_email: recipient address.
    otp: 6-digit code.
    Returns (success: bool, message: str).
    """
    if not to_email or "@" not in to_email:
        return False, "Invalid email address"

    subject = "Your KarnaliX password reset code"
    message = f"Your KarnaliX reset code: {otp}"
    from_email = (
        getattr(settings, "DEFAULT_FROM_EMAIL", None)
        or getattr(settings, "EMAIL_HOST_USER", None)
        or ""
    ).strip()
    if not from_email:
        from_email = None  # Django will use DEFAULT_CHARSET / default

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email or "noreply@karnalix.local",
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True, "Sent"
    except Exception as e:
        logger.exception("Email send failed: %s", e)
        return False, str(e)
