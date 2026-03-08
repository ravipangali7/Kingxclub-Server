"""
Forgot password: search user, send OTP, verify and reset. Unauthenticated.
"""
import random
import string
from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.models import User, PasswordResetOTP, SiteSetting
from core.services.email_service import send_otp_email
from core.services.sms_service import send_sms


def _mask_phone(phone):
    if not phone or len(phone) < 4:
        return "****"
    return "*" * (len(phone) - 4) + phone[-4:]


def _mask_email(email):
    if not email or "@" not in email:
        return "***@***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        m = "***"
    else:
        m = local[0] + "*" * (len(local) - 2) + local[-1] if len(local) > 2 else "***"
    return f"{m}@{domain}"


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password_search(request):
    """
    POST { "phone" | "username" | "email": value }.
    Exact match; return { id, has_phone, has_email, phone_mask?, email_mask?, whatsapp_number? }.
    """
    data = request.data or {}
    phone = data.get("phone") or ""
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()

    user = None
    if phone:
        user = User.objects.filter(phone=phone).first()
    elif username:
        user = User.objects.filter(username=username).first()
    elif email:
        user = User.objects.filter(email=email).first()

    if not user:
        return Response(
            {"detail": "No account found with that information."},
            status=status.HTTP_404_NOT_FOUND,
        )

    has_phone = bool(user.phone and user.phone.strip())
    has_email = bool(user.email and user.email.strip())

    payload = {
        "id": user.id,
        "has_phone": has_phone,
        "has_email": has_email,
    }
    if has_phone:
        payload["phone_mask"] = _mask_phone(user.phone)
    if has_email:
        payload["email_mask"] = _mask_email(user.email)

    # If user has neither, return WhatsApp contact (parent master or site setting)
    if not has_phone and not has_email:
        whatsapp_number = ""
        if user.parent_id and getattr(user.parent, "whatsapp_number", None):
            whatsapp_number = (user.parent.whatsapp_number or "").strip()
        if not whatsapp_number:
            site = SiteSetting.objects.first()
            if site and site.whatsapp_number:
                whatsapp_number = (site.whatsapp_number or "").strip()
        payload["whatsapp_number"] = whatsapp_number or None

    return Response(payload)


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password_send_otp(request):
    """
    POST { "user_id": int, "channel": "phone" | "email" }.
    Generate OTP, store, send (stub). Return success/fail.
    """
    user_id = request.data.get("user_id")
    channel = (request.data.get("channel") or "").strip().lower()
    if channel not in ("phone", "email"):
        return Response({"detail": "channel must be 'phone' or 'email'."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(pk=user_id).first()
    if not user:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    if channel == "phone" and not (user.phone and user.phone.strip()):
        return Response({"detail": "User has no phone."}, status=status.HTTP_400_BAD_REQUEST)
    if channel == "email" and not (user.email and user.email.strip()):
        return Response({"detail": "User has no email."}, status=status.HTTP_400_BAD_REQUEST)

    # Invalidate any existing OTPs for this user
    PasswordResetOTP.objects.filter(user=user).delete()

    otp = "".join(random.choices(string.digits, k=6))
    expires_at = timezone.now() + timedelta(minutes=10)
    PasswordResetOTP.objects.create(user=user, otp=otp, channel=channel, expires_at=expires_at)

    if channel == "phone" and user.phone:
        ok, msg = send_sms(user.phone, f"Your KarnaliX reset code: {otp}")
        if not ok:
            return Response({"detail": msg or "Failed to send SMS."}, status=status.HTTP_502_BAD_GATEWAY)
    if channel == "email" and user.email:
        ok, msg = send_otp_email(user.email, otp)
        if not ok:
            return Response({"detail": msg or "Failed to send email."}, status=status.HTTP_502_BAD_GATEWAY)

    return Response({"detail": "OTP sent."})


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password_verify_reset(request):
    """
    POST { "user_id": int, "otp": str, "new_password": str }.
    Verify OTP and set new password; invalidate OTP.
    """
    user_id = request.data.get("user_id")
    otp = (request.data.get("otp") or "").strip()
    new_password = request.data.get("new_password")

    if not user_id or not otp or not new_password:
        return Response({"detail": "user_id, otp and new_password required."}, status=status.HTTP_400_BAD_REQUEST)
    if len(new_password) < 6:
        return Response({"detail": "Password must be at least 6 characters."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(pk=user_id).first()
    if not user:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    record = (
        PasswordResetOTP.objects.filter(user=user, otp=otp)
        .filter(expires_at__gt=timezone.now())
        .order_by("-created_at")
        .first()
    )
    if not record:
        return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()
    PasswordResetOTP.objects.filter(user=user).delete()

    return Response({"detail": "Password updated. You can now log in."})


@api_view(["GET"])
@permission_classes([AllowAny])
def forgot_password_whatsapp_contact(request):
    """
    GET ?user_id=... — return { whatsapp_number } for user (parent master or site setting).
    """
    user_id = request.query_params.get("user_id")
    if not user_id:
        return Response({"detail": "user_id required."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(pk=user_id).first()
    if not user:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    whatsapp_number = ""
    if user.parent_id and getattr(user.parent, "whatsapp_number", None):
        whatsapp_number = (user.parent.whatsapp_number or "").strip()
    if not whatsapp_number:
        site = SiteSetting.objects.first()
        if site and site.whatsapp_number:
            whatsapp_number = (site.whatsapp_number or "").strip()

    return Response({"whatsapp_number": whatsapp_number or None})
