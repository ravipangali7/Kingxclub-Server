"""
Send SMS via Aakash SMS API (https://sms.aakashsms.com/sms/v3/send).
Token from SuperSetting.sms_api_token or env SMS_API_TOKEN.
"""
import logging
import os

import requests

from core.models import SuperSetting

logger = logging.getLogger(__name__)

AAKASH_SMS_URL = "https://sms.aakashsms.com/sms/v3/send"


def get_sms_token():
    """Return SMS API token from SuperSetting or env."""
    settings = SuperSetting.get_settings()
    if settings and getattr(settings, "sms_api_token", None) and settings.sms_api_token.strip():
        return settings.sms_api_token.strip()
    return (os.environ.get("SMS_API_TOKEN") or "").strip()


def send_sms(to: str, text: str) -> tuple[bool, str]:
    """
    Send SMS to the given number.
    to: 10-digit number, e.g. 9779812345678 (digits only).
    text: message body.
    Returns (success: bool, message: str).
    """
    token = get_sms_token()
    if not token:
        logger.warning("SMS not sent: no sms_api_token in SuperSetting or SMS_API_TOKEN in env")
        return False, "SMS not configured"

    to_digits = "".join(c for c in str(to) if c.isdigit())
    if not to_digits or len(to_digits) < 10:
        return False, "Invalid phone number"

    payload = {
        "auth_token": token,
        "to": to_digits,
        "text": text,
    }
    try:
        resp = requests.post(AAKASH_SMS_URL, data=payload, timeout=15)
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if resp.status_code != 200:
            return False, data.get("message", resp.text or f"HTTP {resp.status_code}")
        if data.get("error") is True:
            return False, data.get("message", "Unknown SMS API error")
        return True, data.get("message", "Sent")
    except requests.RequestException as e:
        logger.exception("SMS request failed: %s", e)
        return False, str(e)
