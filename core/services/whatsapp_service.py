"""
Stub for sending OTP via WhatsApp (e.g. WhatsApp Business API / Twilio).
When configured, implement send_whatsapp_otp(to, text) and return (True, "Sent").
Until then, returns (False, "WhatsApp OTP not configured") so frontend can prompt SMS.
"""
import logging

logger = logging.getLogger(__name__)


def send_whatsapp_otp(to: str, text: str) -> tuple[bool, str]:
    """
    Send OTP message to the given number via WhatsApp.
    to: full phone with country code (digits only), e.g. 9779812345678.
    text: message body (e.g. "Your KarnaliX verification code: 123456").
    Returns (success: bool, message: str).
    """
    # TODO: Integrate WhatsApp Business API (e.g. Twilio, Meta Cloud API) when available.
    logger.warning("WhatsApp OTP not configured; use SMS for signup.")
    return False, "WhatsApp OTP not configured"
