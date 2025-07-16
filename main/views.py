from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import AdminUserSerializer, CustomTokenObtainPairSerializer
from .models import AdminUser
from .serializers import RegisterSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

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

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        try:
            user = AdminUser.objects.get(email=email)
        except AdminUser.DoesNotExist:
            return Response({'message': 'If the email exists, a reset link will be sent.'}, status=200)

        token = default_token_generator.make_token(user)
        
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://duespay.vercel.app')
        reset_url = f"{frontend_url}/reset-password?token={token}&uid={user.pk}"
        
        # Context for email template
        context = {
            'user': user,
            'reset_url': reset_url,
            'now': timezone.now(),
        }
        
        # Render HTML template
        html_content = render_to_string('emails/password_reset.html', context)
        
        # Create email message
        msg = EmailMultiAlternatives(
            subject='Password Reset - DuesPay',
            body=f'Click the link to reset your password: {reset_url}',  # Plain text fallback
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        return Response({'message': 'If the email exists, a reset link will be sent.'}, status=200)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']
        uid = serializer.validated_data['uid']  # Get uid from request body, not query params

        try:
            user = AdminUser.objects.get(pk=uid)
        except AdminUser.DoesNotExist:
            return Response({'message': 'Invalid user.'}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({'message': 'Invalid or expired token.'}, status=400)

        user.set_password(password)
        user.save()
        return Response({'message': 'Password has been reset successfully.'}, status=200)


