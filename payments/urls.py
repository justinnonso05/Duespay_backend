from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ReceiverBankAccountViewSet, PaymentItemViewSet


router = DefaultRouter()

router.register('bank-account', ReceiverBankAccountViewSet)
router.register('payment-items', PaymentItemViewSet)

urlpatterns = router.urls