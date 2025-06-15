from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AssociationViewSet, ProofAndTransactionView, 
    PaymentItemViewSet, TransactionViewSet, 
    ReceiverBankAccountViewSet, RetrieveAssociationViewSet, 
    PayerViewSet, UserProfileView, PayerCheckView
)

router = DefaultRouter()

router.register('association', AssociationViewSet)
router.register('payment-items', PaymentItemViewSet)
router.register('transactions', TransactionViewSet)
router.register('bank-account', ReceiverBankAccountViewSet)
router.register('payers', PayerViewSet)

urlpatterns = router.urls + [
    path('get-association/<str:association_short_name>/', RetrieveAssociationViewSet.as_view(), name='retrieve-association'),
    path('verify-and-create/', ProofAndTransactionView.as_view(), name='verify-and-create'),
    path('adminuser/', UserProfileView.as_view(), name='user-profile'),
    path('payer-check/', PayerCheckView.as_view(), name='payer-check'),
]
