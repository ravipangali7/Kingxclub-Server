"""
Client for external game provider API: getProvider, providerGame, launch_game.
Uses AES-256-ECB for launch_game payload encryption.
"""
import json
from urllib.parse import urlencode
import base64
import time
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


def _ensure_32_bytes(secret_key: str) -> bytes:
    """Ensure secret is 32 bytes for AES-256."""
    key = secret_key.encode("utf-8") if isinstance(secret_key, str) else secret_key
    if len(key) < 32:
        key = key.ljust(32, b"\0")
    elif len(key) > 32:
        key = key[:32]
    return key


def encrypt_payload(data: dict, secret_key: str) -> str:
    """
    Encrypt JSON payload with AES-256-ECB, Base64 encode.
    data: dict with user_id, wallet_amount (number), game_uid, token, timestamp.
    """
    key = _ensure_32_bytes(secret_key)
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    padded = pad(raw, AES.block_size, style="pkcs7")
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode("ascii")


def get_providers(base_url: str, timeout: int = 30) -> list:
    """
    GET {base_url}/getProvider. Returns list of dicts with 'code' and 'name'.
    Handles array of strings (code as name) or array of objects (code/name or similar).
    """
    url = base_url.rstrip("/") + "/getProvider"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if isinstance(item, str):
            result.append({"code": item, "name": item})
        elif isinstance(item, dict):
            code = item.get("code") or item.get("provider") or item.get("id") or ""
            name = item.get("name") or item.get("displayName") or code
            if code:
                result.append({"code": str(code), "name": str(name)})
    return result


def get_provider_games(
    base_url: str,
    provider: str,
    count: int = 50,
    game_type: str | None = None,
    timeout: int = 30,
) -> list:
    """
    GET {base_url}/providerGame?provider=...&count=...
    Returns list of dicts: game_name, game_code, game_type, game_image.
    """
    url = base_url.rstrip("/") + "/providerGame"
    params = {"provider": provider, "count": count}
    if game_type:
        params["type"] = game_type
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if isinstance(item, dict):
            result.append({
                "game_name": item.get("game_name") or item.get("name") or "",
                "game_code": item.get("game_code") or item.get("code") or "",
                "game_type": item.get("game_type") or item.get("type") or "",
                "game_image": item.get("game_image") or item.get("image") or "",
            })
    return result


def build_launch_url(
    base_url: str,
    secret_key: str,
    token: str,
    user_id: str,
    wallet_amount: float | int,
    game_uid: str,
    domain_url: str | None = None,
    callback_url: str | None = None,
) -> str:
    """
    Build the launch URL string only (no HTTP request).
    Returns full URL with query params: user_id, wallet_amount, game_uid, token, timestamp, payload.
    If callback_url is provided, include it in the encrypted payload so the provider can POST round results there.
    """
    ts = str(int(time.time() * 1000))
    payload_data = {
        "user_id": user_id,
        "wallet_amount": float(wallet_amount),
        "game_uid": game_uid,
        "token": token,
        "timestamp": ts,
    }
    if domain_url:
        payload_data["domain_url"] = domain_url.rstrip("/")
    if callback_url:
        payload_data["callback_url"] = callback_url.rstrip("/")
    payload_b64 = encrypt_payload(payload_data, secret_key)
    if "launch" in base_url:
        url = base_url.rstrip("/")
    else:
        url = base_url.rstrip("/") + "/launch_game"
    params = {
        "user_id": user_id,
        "wallet_amount": int(round(float(wallet_amount))),
        "game_uid": game_uid,
        "token": token,
        "timestamp": ts,
        "payload": payload_b64,
    }
    temp = url + "?" + urlencode(params)
    print(f"CHEKC IT {temp}")
    return temp


def launch_game(
    base_url: str,
    secret_key: str,
    token: str,
    user_id: str,
    wallet_amount: float | int,
    game_uid: str,
    domain_url: str | None = None,
    timeout: int = 30,
    allow_redirects: bool = False,
):
    """
    Build AES-256-ECB encrypted payload and GET launch_game.
    If domain_url is provided, include it in the payload (same as PHP reference).
    Returns response object; if redirect, final_url is in response.url.
    Set allow_redirects=False to get redirect URL without following.
    """
    ts = str(int(time.time() * 1000))
    payload_data = {
        "user_id": user_id,
        "wallet_amount": float(wallet_amount),
        "game_uid": game_uid,
        "token": token,
        "timestamp": ts,
    }
    if domain_url:
        payload_data["domain_url"] = domain_url.rstrip("/")
    payload_b64 = encrypt_payload(payload_data, secret_key)
    if "launch" in base_url:
        url = base_url.rstrip("/")
    else:
        url = base_url.rstrip("/") + "/launch_game"
    params = {
        "user_id": user_id,
        "wallet_amount": int(round(float(wallet_amount))),
        "game_uid": game_uid,
        "token": token,
        "timestamp": ts,
        "payload": payload_b64,
    }
    r = requests.get(url, params=params, timeout=timeout, allow_redirects=allow_redirects)
    return r
