"""
Sync URL Configuration
"""
from django.urls import path

from .views import SyncStartView, SyncStatusView, SyncStopView

urlpatterns = [
    path('start/', SyncStartView.as_view(), name='sync-start'),
    path('status/', SyncStatusView.as_view(), name='sync-status'),
    path('stop/', SyncStopView.as_view(), name='sync-stop'),
]
