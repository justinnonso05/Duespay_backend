from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PayerViewSet, PayerCheckView

router = DefaultRouter()

router.register('payers', PayerViewSet)

urlpatterns = router.urls + [
    path('payer-check/', PayerCheckView.as_view(), name='payer-check'),
]
