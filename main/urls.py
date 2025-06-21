from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserProfileView

urlpatterns = [
    path('adminuser/', UserProfileView.as_view(), name='user-profile'),
]
    