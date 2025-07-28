"""
ASGI config for exam_geenie project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
# import exam.routing
# from ..exams import routing as exam_routing
# from exams import routing as exam_routing


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exam_geenie.settings")

django.setup()

# application = get_asgi_application()
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            __import__('exams.routing').routing.websocket_urlpatterns
            # exam_routing.websocket_urlpatterns
        )
    ),
})
