from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'folders'

router = DefaultRouter()
router.register('', views.FolderViewSet, basename='folder')

urlpatterns = [
    path('', include(router.urls)),
]
