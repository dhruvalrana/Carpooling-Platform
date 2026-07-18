"""WSGI config for carpool_project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carpool_project.settings.dev')
application = get_wsgi_application()
