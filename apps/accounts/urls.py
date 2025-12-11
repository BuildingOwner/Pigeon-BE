from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # OAuth
    path('google/login/', views.GoogleLoginView.as_view(), name='google-login'),
    path('google/callback/', views.GoogleCallbackView.as_view(), name='google-callback'),

    # JWT Token
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # User Info
    path('me/', views.UserMeView.as_view(), name='user-me'),
]
