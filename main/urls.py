from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GoogleLoginView, UserProfileView, ping_view, InitiatePaymentView, korapay_webhook, PaymentStatusView

urlpatterns = [
    path('adminuser/', UserProfileView.as_view(), name='user-profile'),
    path('ping/', ping_view, name='ping-view'),
    path('payment/initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('payment/status/<str:reference_id>/', PaymentStatusView.as_view(), name='payment-status'),
    path('webhook/korapay/', korapay_webhook, name='korapay-webhook'),
]
