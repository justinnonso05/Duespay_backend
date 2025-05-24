from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaySpaceViewSet, RegisterView, PaymentItemViewSet

router = DefaultRouter()

router.register('spaces', PaySpaceViewSet)
router.register('payment_items', PaymentItemViewSet)

urlpatterns = router.urls
