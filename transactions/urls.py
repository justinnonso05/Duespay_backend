from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProofAndTransactionView, TransactionViewSet, TransactionReceiptDetailView


router = DefaultRouter()

router.register('transactions', TransactionViewSet)

urlpatterns = router.urls + [
    path('verify-and-create/', ProofAndTransactionView.as_view(), name='verify-and-create'),
    path('receipts/<str:receipt_no>/', TransactionReceiptDetailView.as_view(), name='receipt-detail'),
]
