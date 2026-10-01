from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.auth_views import current_user, current_client, obtain_client_auth_token, obtain_admin_auth_token
from accounts.email_auth import (
    ForgotPasswordView, RegisterView, ResendVerificationView,
    ResetPasswordView, VerifyEmailView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", obtain_admin_auth_token, name="api-token"),
    path("api/auth/admin/login/", obtain_admin_auth_token, name="admin-login"),
    path("api/auth/login/", obtain_client_auth_token, name="api-login"),
    path("api/auth/me/", current_client, name="current-client"),
    path("api/auth/admin/me/", current_user, name="current-user"),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("api/auth/resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("api/auth/forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("api/auth/reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/", include("gateway.api_urls")),
]
