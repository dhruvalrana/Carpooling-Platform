"""
ASGI config for carpool_project — supports both HTTP and WebSocket via Channels.
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import tracking.routing
import chat.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carpool_project.settings.dev')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            tracking.routing.websocket_urlpatterns +
            chat.routing.websocket_urlpatterns
        )
    ),
})
