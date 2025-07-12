from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import AssociationViewSet, NotificationViewSet, RetrieveAssociationViewSet

router = DefaultRouter()

router.register('association', AssociationViewSet)
router.register('notifications', NotificationViewSet)

urlpatterns = router.urls + [
    path('get-association/<str:association_short_name>/', RetrieveAssociationViewSet.as_view(), name='retrieve-association'),
]
