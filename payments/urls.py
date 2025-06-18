from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ReceiverBankAccountViewSet


router = DefaultRouter()

router.register('bank-account', ReceiverBankAccountViewSet)

urlpatterns = []