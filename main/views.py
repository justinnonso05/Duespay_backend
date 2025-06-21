from django.shortcuts import redirect
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import AdminUserSerializer, CustomTokenObtainPairSerializer
from .models import AdminUser
from .serializers import  RegisterSerializer

def base_redirect_view(request):
    """
    Redirects to the admin page.
    """
    return redirect('/admin/')  # Adjust the URL as needed for your admin page
  
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminUserSerializer  # or AdminUserSerializer if you want admin info
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Return the current user (AdminUser or Payer)
        user = self.request.user
        # If you want to return the Payer profile linked to the user:
        if hasattr(user, 'payer'):
            return user.payer
        return user  # fallback for AdminUser


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    queryset = AdminUser.objects.all()
 

