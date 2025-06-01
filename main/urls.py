from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AssociationViewSet, RegisterView, 
    PaymentItemViewSet, TransactionViewSet, 
    ReceiverBankAccountViewSet, RetrieveAssociationViewSet
)

router = DefaultRouter()

router.register('association', AssociationViewSet)
router.register('payment-items', PaymentItemViewSet)
router.register('transactions', TransactionViewSet)
router.register('bank-account', ReceiverBankAccountViewSet)

urlpatterns = router.urls + [
    path('get-association/<str:association_short_name>/', RetrieveAssociationViewSet.as_view(), name='retrieve-association'),
    ]
