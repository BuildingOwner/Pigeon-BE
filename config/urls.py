"""
URL configuration for Pigeon project.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/', include([
        # API Documentation
        path('schema/', SpectacularAPIView.as_view(), name='schema'),
        path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

        # App URLs
        path('auth/', include('apps.accounts.urls')),
        path('mails/', include('apps.mails.urls')),
        path('folders/', include('apps.folders.urls')),
        path('classification/', include('apps.classifier.urls')),
    ])),
]
