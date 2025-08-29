from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BankListView,
    PaymentItemViewSet,
    ReceiverBankAccountViewSet,
    VerifyBankAccountView,
)

router = DefaultRouter()

router.register("bank-account", ReceiverBankAccountViewSet)
router.register("payment-items", PaymentItemViewSet)

urlpatterns = [
    path("bank-account/all-banks/", BankListView.as_view(), name="bank-list"),
    path("bank-account/verify/", VerifyBankAccountView.as_view(), name="verify-bank"),
] + router.urls
