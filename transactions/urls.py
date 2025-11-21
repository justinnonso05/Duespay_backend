from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    InitiatePaymentView,
    PaymentStatusView,
    TransactionReceiptDetailView,
    TransactionViewSet,
    paystack_webhook,
)

router = DefaultRouter()
router.register("", TransactionViewSet)

urlpatterns = [
    path("webhook/", paystack_webhook, name="paystack-webhook"),  # Updated
    path(
        "receipts/<str:receipt_id>/",
        TransactionReceiptDetailView.as_view(),
        name="receipt-detail",
    ),
    path("payment/initiate/", InitiatePaymentView.as_view(), name="initiate-payment"),  # Card + Bank  # Bank only
    path(
        "payment/status/<str:reference_id>/",
        PaymentStatusView.as_view(),
        name="payment-status",
    ),
] + router.urls  # Router URLs LAST