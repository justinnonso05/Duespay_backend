from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import TokenRefreshView

from main.views import (
    CustomTokenObtainPairView,
    GoogleLoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    logout_all,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/association/", include("association.urls")),
    path("api/payers/", include("payers.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/transactions/", include("transactions.urls")),
    path("api/main/", include("main.urls")),
    # auth
    path("api/auth/google/", GoogleLoginView.as_view(), name="google-login"),
    path(
        "api/auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"
    ),
    path("api/auth/logout/", logout_all, name="logout-all"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path(
        "api/auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "api/auth/password-reset-confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    # swagger
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
