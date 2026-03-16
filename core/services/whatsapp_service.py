"""
Send OTP via Flexgrew WhatsApp API.
When FLEXGREW_API_KEY is set in settings, create/find contact, start chat, send text.
Otherwise returns (False, "WhatsApp OTP not configured").
"""
import logging

import requests

from django.conf import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15


def get_flexgrew_api_key() -> str:
    """Return Flexgrew API key from Django settings."""
    return (getattr(settings, "FLEXGREW_API_KEY", None) or "").strip()


def get_flexgrew_base_url() -> str:
    """Return Flexgrew API base URL (no trailing slash) from Django settings."""
    url = (getattr(settings, "FLEXGREW_BASE_URL", None) or "https://flexgrew.cloud/api").strip()
    return url.rstrip("/")


def _phone_to_e164(phone: str) -> str:
    """Normalize to E.164 with + (e.g. +9779812345678)."""
    digits = "".join(c for c in str(phone).strip() if c.isdigit())
    if not digits:
        return ""
    return "+" + digits


def _create_or_get_contact(base_url: str, headers: dict, phone_e164: str) -> tuple[bool, int | None, str]:
    """
    Create contact or get existing. Returns (ok, contact_id, error_message).
    """
    payload = {"first_name": "User", "phone": phone_e164}
    try:
        resp = requests.post(
            f"{base_url}/contacts",
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        logger.exception("Flexgrew create contact request failed: %s", e)
        return False, None, str(e)

    if resp.status_code == 201:
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        cid = data.get("id")
        if cid is not None:
            return True, int(cid), ""
        return False, None, "Invalid create contact response"

    if resp.status_code == 409:
        # Contact already exists; search by phone to get id
        try:
            search_resp = requests.get(
                f"{base_url}/contacts",
                params={"search": phone_e164, "limit": 1},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            logger.exception("Flexgrew contacts search failed: %s", e)
            return False, None, str(e)
        if search_resp.status_code != 200:
            return False, None, "Could not find existing contact"
        data = search_resp.json() if search_resp.headers.get("content-type", "").startswith("application/json") else {}
        items = data.get("data") or []
        if items and isinstance(items[0], dict) and items[0].get("id") is not None:
            return True, int(items[0]["id"]), ""
        return False, None, "Contact exists but could not retrieve id"

    # 401, 429, 500, etc.
    if resp.status_code == 401:
        logger.warning("Flexgrew API key invalid or expired")
        return False, None, "WhatsApp service error"
    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    msg = data.get("message", resp.text or f"HTTP {resp.status_code}")
    return False, None, msg


def _start_chat(base_url: str, headers: dict, contact_id: int) -> tuple[bool, str | None, str]:
    """Start or get chat for contact. Returns (ok, chat_uuid, error_message)."""
    try:
        resp = requests.post(
            f"{base_url}/chats/start",
            json={"contactId": contact_id},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        logger.exception("Flexgrew start chat request failed: %s", e)
        return False, None, str(e)

    if resp.status_code not in (200, 201):
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        msg = data.get("message", resp.text or f"HTTP {resp.status_code}")
        return False, None, msg

    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    uuid_val = data.get("uuid")
    if uuid_val:
        return True, str(uuid_val), ""
    return False, None, "Invalid start chat response"


def _send_text_message(base_url: str, headers: dict, chat_uuid: str, text: str) -> tuple[bool, str]:
    """Send text message to chat. Returns (success, error_message)."""
    try:
        resp = requests.post(
            f"{base_url}/chats/{chat_uuid}/messages",
            json={"message": text, "type": "text"},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        logger.exception("Flexgrew send message request failed: %s", e)
        return False, str(e)

    if resp.status_code in (200, 201):
        return True, ""
    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    return False, data.get("message", resp.text or f"HTTP {resp.status_code}")


def send_whatsapp_otp(to: str, text: str) -> tuple[bool, str]:
    """
    Send OTP message to the given number via Flexgrew WhatsApp API.
    to: full phone with country code (digits only), e.g. 9779812345678.
    text: message body (e.g. "Your KarnaliX verification code: 123456").
    Returns (success: bool, message: str).
    """
    api_key = get_flexgrew_api_key()
    if not api_key:
        logger.warning("WhatsApp OTP not configured; FLEXGREW_API_KEY not set.")
        return False, "WhatsApp OTP not configured"

    phone_e164 = _phone_to_e164(to)
    if not phone_e164 or len(phone_e164) < 11:
        return False, "Invalid phone number"

    base_url = get_flexgrew_base_url()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    ok, contact_id, err = _create_or_get_contact(base_url, headers, phone_e164)
    if not ok:
        return False, err or "Failed to create or find contact"

    ok, chat_uuid, err = _start_chat(base_url, headers, contact_id)
    if not ok:
        return False, err or "Failed to start chat"

    ok, err = _send_text_message(base_url, headers, chat_uuid, text)
    if not ok:
        return False, err or "Failed to send message"

    return True, "Sent"
