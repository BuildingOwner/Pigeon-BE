from django.urls import path

from . import views

app_name = 'classifier'

urlpatterns = [
    path('classify/', views.ClassifyView.as_view(), name='classify'),
    path('classify-unclassified/', views.ClassifyUnclassifiedView.as_view(), name='classify-unclassified'),
]
