from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.auth_views import current_user, obtain_client_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", obtain_client_auth_token, name="api-token"),
    path("api/auth/login/", obtain_client_auth_token, name="api-login"),
    path("api/auth/me/", current_user, name="current-user"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/", include("gateway.api_urls")),
]
