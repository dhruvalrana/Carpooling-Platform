"""Root URL configuration for carpool_project."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth
    path('', include('accounts.urls')),
    # App modules
    path('vehicles/', include('vehicles.urls')),
    path('rides/', include('rides.urls')),
    path('trips/', include('trips.urls')),
    path('tracking/', include('tracking.urls')),
    path('payments/', include('payments.urls')),
    path('wallet/', include('wallet.urls')),
    path('reports/', include('reports.urls')),
    path('notifications/', include('notifications.urls')),
    # REST API
    path('api/', include('accounts.api_urls')),
    path('api/', include('vehicles.api_urls')),
    path('api/', include('rides.api_urls')),
    path('api/', include('trips.api_urls')),
    path('api/', include('tracking.api_urls')),
    path('api/', include('chat.api_urls')),
    path('api/', include('payments.api_urls')),
    path('api/', include('wallet.api_urls')),
    path('api/', include('reports.api_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
