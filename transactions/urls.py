from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    InitiatePaymentView,
    PaymentStatusView,
    TransactionReceiptDetailView,
    TransactionViewSet,
    korapay_webhook,
)

router = DefaultRouter()

router.register("", TransactionViewSet)

urlpatterns = router.urls + [
    path(
        "receipts/<str:receipt_id>/",
        TransactionReceiptDetailView.as_view(),
        name="receipt-detail",
    ),
    path("payment/initiate/", InitiatePaymentView.as_view(), name="initiate-payment"),
    path(
        "payment/status/<str:reference_id>/",
        PaymentStatusView.as_view(),
        name="payment-status",
    ),
    path("webhook/korapay/", korapay_webhook, name="korapay-webhook"),
]
