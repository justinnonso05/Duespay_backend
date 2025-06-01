from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AssociationViewSet, ProofVerificationView, 
    PaymentItemViewSet, TransactionViewSet, 
    ReceiverBankAccountViewSet, RetrieveAssociationViewSet,
    TransactionCreateView
)

router = DefaultRouter()

router.register('association', AssociationViewSet)
router.register('payment-items', PaymentItemViewSet)
router.register('transactions', TransactionViewSet)
router.register('bank-account', ReceiverBankAccountViewSet)

urlpatterns = router.urls + [
    path('get-association/<str:association_short_name>/', RetrieveAssociationViewSet.as_view(), name='retrieve-association'),
    path('api/verify-proof/', ProofVerificationView.as_view(), name='verify-proof'),
    path('api/transaction/create/', TransactionCreateView.as_view(), name='transaction-create'),
]
