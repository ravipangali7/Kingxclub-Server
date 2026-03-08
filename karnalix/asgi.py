"""
ASGI config for karnalix project.
Serves HTTP via Django and WebSocket via Channels (message consumer).
Run with Daphne for WebSocket support: daphne -b 0.0.0.0 -p 8000 karnalix.asgi:application
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "karnalix.settings")

import django
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from core.auth_middleware import TokenAuthMiddleware
from core.routing import websocket_urlpatterns

django_asgi = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi,
        "websocket": TokenAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)