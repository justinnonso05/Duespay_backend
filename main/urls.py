from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserProfileView, ping_view

urlpatterns = [
    path('adminuser/', UserProfileView.as_view(), name='user-profile'),
    path('ping/', ping_view, name='ping-view'),
]
    