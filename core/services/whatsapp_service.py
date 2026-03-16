"""
Send OTP via Flexgrew WhatsApp API.
When FLEXGREW_API_KEY is set in settings, create/find contact, start chat, send text.
Otherwise returns (False, "WhatsApp OTP not configured").
"""
import requests

from django.conf import settings

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
    Uses POST {base_url}/contacts (e.g. https://flexgrew.cloud/api/contacts).
    """
    url = f"{base_url}/contacts"
    payload = {"first_name": "User", "phone": phone_e164}
    print(f"Flexgrew POST {url}")
    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        print(f"Flexgrew create contact request failed: {e}")
        return False, None, str(e)

    if resp.status_code == 201:
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        cid = data.get("id")
        if cid is not None:
            print(f"Flexgrew contact created: id={cid} phone={phone_e164[:6]}***")
            return True, int(cid), ""
        print(f"Flexgrew create contact 201 but no id in response: {data}")
        return False, None, "Invalid create contact response"

    if resp.status_code == 409:
        # Contact already exists; search by phone to get id
        print(f"Flexgrew contact exists (409), searching by phone={phone_e164[:6]}***")
        try:
            search_resp = requests.get(
                f"{base_url}/contacts",
                params={"search": phone_e164, "limit": 5},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            print(f"Flexgrew contacts search failed: {e}")
            return False, None, str(e)
        if search_resp.status_code != 200:
            print(f"Flexgrew contacts search returned {search_resp.status_code}: {search_resp.text[:200]}")
            return False, None, "Could not find existing contact"
        data = search_resp.json() if search_resp.headers.get("content-type", "").startswith("application/json") else {}
        items = data.get("data") or []
        # Match by phone (API may return multiple; find exact match)
        for item in items:
            if isinstance(item, dict):
                cid = item.get("id")
                if cid is not None:
                    item_phone = (item.get("phone") or "").strip().replace(" ", "")
                    if item_phone == phone_e164 or (item.get("phone") or "").strip() == phone_e164:
                        print(f"Flexgrew found existing contact: id={cid}")
                        return True, int(cid), ""
        if items and isinstance(items[0], dict) and items[0].get("id") is not None:
            print(f"Flexgrew using first search result as contact: id={items[0]['id']}")
            return True, int(items[0]["id"]), ""
        print(f"Flexgrew 409 but search returned no usable contact: data={data}")
        return False, None, "Contact exists but could not retrieve id"

    # 401, 429, 500, 404, etc.
    try:
        err_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    except Exception:
        err_data = {}
    if resp.status_code == 404:
        print(f"Flexgrew 404: POST {url} not found. Check FLEXGREW_BASE_URL (expected https://flexgrew.cloud/api).")
        return False, None, "WhatsApp API endpoint not found (404). Check API base URL."
    msg = err_data.get("message", resp.text[:200] if resp.text else f"HTTP {resp.status_code}")
    if resp.status_code == 401:
        print("Flexgrew API key invalid or expired (401). Check FLEXGREW_API_KEY in settings.")
    else:
        print(f"Flexgrew create contact failed: status={resp.status_code} message={msg}")
    return False, None, msg if resp.status_code != 401 else "WhatsApp service error"


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
        print(f"Flexgrew start chat request failed: {e}")
        return False, None, str(e)

    if resp.status_code not in (200, 201):
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        msg = data.get("message", resp.text or f"HTTP {resp.status_code}")
        print(f"Flexgrew start chat failed: status={resp.status_code} contact_id={contact_id} message={msg}")
        return False, None, msg

    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    uuid_val = data.get("uuid")
    if uuid_val:
        print(f"Flexgrew chat started: contact_id={contact_id} uuid={uuid_val[:8]}...")
        return True, str(uuid_val), ""
    print(f"Flexgrew start chat response missing uuid: {data}")
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
        print(f"Flexgrew send message request failed: {e}")
        return False, str(e)

    if resp.status_code in (200, 201):
        print("Flexgrew message sent successfully")
        return True, ""
    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    msg = data.get("message", resp.text or f"HTTP {resp.status_code}")
    print(f"Flexgrew send message failed: status={resp.status_code} message={msg}")
    return False, msg


def send_whatsapp_otp(to: str, text: str) -> tuple[bool, str]:
    """
    Send OTP message to the given number via Flexgrew WhatsApp API.
    to: full phone with country code (digits only), e.g. 9779812345678.
    text: message body (e.g. "Your KarnaliX verification code: 123456").
    Returns (success: bool, message: str).
    """
    api_key = get_flexgrew_api_key()
    if not api_key:
        print("WhatsApp OTP not configured; FLEXGREW_API_KEY not set in settings.")
        return False, "WhatsApp OTP not configured"

    phone_e164 = _phone_to_e164(to)
    if not phone_e164 or len(phone_e164) < 11:
        print(f"WhatsApp OTP invalid phone: to={to[:8]}*** e164={phone_e164 or 'empty'}")
        return False, "Invalid phone number"

    base_url = get_flexgrew_base_url()
    print(f"WhatsApp OTP: sending to {phone_e164[:6]}*** via {base_url}")
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
