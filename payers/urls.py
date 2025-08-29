from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PayerCheckView, PayerViewSet

router = DefaultRouter()

router.register("", PayerViewSet)

urlpatterns = [
    path('check/', PayerCheckView.as_view(), name='payer-check'),  # /api/payers/check/
] + router.urls