from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    InitiatePaymentView,
    PaymentStatusView,
    TransactionReceiptDetailView,
    TransactionViewSet,
    korapay_webhook,
    InitiateBankTransferView,
)

router = DefaultRouter()
router.register("", TransactionViewSet)

urlpatterns = [
    path("webhook/", korapay_webhook, name="korapay-webhook"),
    path(
        "receipts/<str:receipt_id>/",
        TransactionReceiptDetailView.as_view(),
        name="receipt-detail",
    ),
    path("payment/initiate/", InitiateBankTransferView.as_view(), name="initiate-payment"),
    path(
        "payment/status/<str:reference_id>/",
        PaymentStatusView.as_view(),
        name="payment-status",
    ),
] + router.urls  # Router URLs LAST