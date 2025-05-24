from rest_framework import viewsets, generics
from django.contrib.auth.models import User
from .models import PaySpace, PaymentItem
from .serializers import PaySpaceSerializer, PaymentItemSerializer, RegisterSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    queryset = User.objects.all()

class PaySpaceViewSet(viewsets.ModelViewSet):
    queryset = PaySpace.objects.all()
    serializer_class = PaySpaceSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(admin=self.request.user)

class PaymentItemViewSet(viewsets.ModelViewSet):
    queryset = PaymentItem.objects.all()
    serializer_class = PaymentItemSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(pay_space=self.request.user.pay_space)