"""
ASGI middleware: authenticate WebSocket connections using token from query string.
Attaches scope["user"] for valid Token; scope["user"] is AnonymousUser if invalid/missing.
"""
import urllib.parse
from asgiref.sync import sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token


@sync_to_async
def get_user_from_token(token_key):
    if not token_key or not isinstance(token_key, str):
        return AnonymousUser()
    try:
        token = Token.objects.select_related("user").get(key=token_key.strip())
        return token.user
    except (Token.DoesNotExist, ValueError):
        return AnonymousUser()


class TokenAuthMiddleware:
    """Populate scope["user"] from query string ?token=... for WebSocket connections."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "websocket":
            qs = scope.get("query_string", b"").decode()
            params = urllib.parse.parse_qs(qs)
            token = (params.get("token") or [None])[0]
            scope = dict(scope)
            scope["user"] = await get_user_from_token(token)
        await self.app(scope, receive, send)
