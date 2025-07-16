from django.http import HttpResponse
from django.shortcuts import redirect
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import AdminUserSerializer, CustomTokenObtainPairSerializer
from .models import AdminUser
from .serializers import  RegisterSerializer

def base_redirect_view(request):
    return redirect('/admin/')  

def ping_view(request):
    print("Server is running")
    return HttpResponse("Pong", status=200)  

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminUserSerializer  
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        if hasattr(user, 'payer'):
            return user.payer
        return user  

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    queryset = AdminUser.objects.all()
 
