from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'mails'

router = DefaultRouter()
router.register('', views.MailViewSet, basename='mail')

urlpatterns = [
    path('', include(router.urls)),
]
