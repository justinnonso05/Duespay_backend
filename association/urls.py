from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import AssociationViewSet, RetrieveAssociationViewSet

router = DefaultRouter()

router.register('association', AssociationViewSet)

urlpatterns = router.urls + [
    path('get-association/<str:association_short_name>/', RetrieveAssociationViewSet.as_view(), name='retrieve-association'),
]
