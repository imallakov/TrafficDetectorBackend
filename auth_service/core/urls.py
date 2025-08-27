"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from rest_framework import permissions

from .views import validate_token, RegisterView, CustomTokenObtainPairView, CustomTokenRefreshView, LogoutView, \
    PasswordResetRequestView, PasswordResetValidateOTPView, PasswordResetConfirmView, EmailVerificationRequestView, \
    EmailVerificationConfirmView

from drf_spectacular.views import (
    SpectacularAPIView,  # OpenAPI schema (JSON)
    SpectacularSwaggerView,  # Swagger UI
    SpectacularRedocView,  # ReDoc
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("auth/register/", RegisterView.as_view(), name='register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password-reset/validate/', PasswordResetValidateOTPView.as_view(), name='password-reset-validate'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    path('auth/email-verify/request/', EmailVerificationRequestView.as_view(), name='email-verification-request'),
    path('auth/email-verify/confirm/', EmailVerificationConfirmView.as_view(), name='email-verification-confirm'),

    path("auth/validate-token/", validate_token, name="validate_token"),

    path(f'schema/', SpectacularAPIView.as_view(), name='schema'),
    path(f'docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path(f'redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
