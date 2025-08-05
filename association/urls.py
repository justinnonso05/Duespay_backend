from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    AssociationViewSet, NotificationViewSet, RetrieveAssociationViewSet,
    SessionViewSet, AssociationProfileView
)

router = DefaultRouter()

router.register('association', AssociationViewSet)
router.register('notifications', NotificationViewSet)
router.register('sessions', SessionViewSet, basename='session')

urlpatterns = [
    path('get-association/<str:association_short_name>/', RetrieveAssociationViewSet.as_view(), name='retrieve-association'),
    path('association/profile/', AssociationProfileView.as_view(), name='association-profile'),
] + router.urls 
