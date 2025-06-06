import json
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import models
from rest_framework.permissions import IsAuthenticated, AllowAny
from .services import VerificationService
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from .models import (
    Association, PaymentItem, ReceiverBankAccount, Payer,
    TransactionReceipt, Transaction, AdminUser
)
from .serializers import (
    AssociationSerializer, PaymentItemSerializer, 
    RegisterSerializer, TransactionSerializer, 
    ReceiverBankAccountSerializer
)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    queryset = AdminUser.objects.all()

class AssociationViewSet(viewsets.ModelViewSet):
    queryset = Association.objects.all()
    serializer_class = AssociationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        association = getattr(self.request.user, 'association', None)
        if association:
            return Association.objects.filter(pk=association.pk)
        return Association.objects.none()

    def perform_create(self, serializer):
        serializer.save(admin=self.request.user)


class RetrieveAssociationViewSet(generics.RetrieveAPIView):
    queryset = Association.objects.all()
    serializer_class = AssociationSerializer
    lookup_field = 'association_short_name'
    permission_classes = [AllowAny]

class PaymentItemViewSet(viewsets.ModelViewSet):
    queryset = PaymentItem.objects.all()
    serializer_class = PaymentItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return only payment items for the association of the authenticated user
        association = getattr(self.request.user, 'association', None)
        if association:
            return PaymentItem.objects.filter(association=association)
        return PaymentItem.objects.none()

    def perform_create(self, serializer):
        serializer.save(association=self.request.user.association)

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(payer=self.request.user.payer)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).order_by('-submitted_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        # --- Meta Data Calculation ---
        # Total Collections
        # models = 
        total_collections = queryset.aggregate(total=models.Sum('amount_paid'))['total'] or 0

        # Completed Payments (assuming is_verified=True means completed)
        completed_count = queryset.filter(is_verified=True).count()

        # Pending Payments (assuming is_verified=False means pending)
        pending_count = queryset.filter(is_verified=False).count()

        # Example: Calculate percentage changes (dummy values, replace with your logic)
        # You can compare with previous month, week, etc.
        percent_collections = "+12%"  # Replace with actual calculation
        percent_completed = "+8%"     # Replace with actual calculation
        percent_pending = "-2%"       # Replace with actual calculation

        meta = {
            "total_collections": total_collections,
            "completed_payments": completed_count,
            "pending_payments": pending_count,
            "percent_collections": percent_collections,
            "percent_completed": percent_completed,
            "percent_pending": percent_pending,
        }

        paginated_response = self.get_paginated_response(data)
        response_data = paginated_response.data
        response_data['meta'] = meta
        return Response(response_data)


class ReceiverBankAccountViewSet(viewsets.ModelViewSet):
    queryset = ReceiverBankAccount.objects.all()
    serializer_class = ReceiverBankAccountSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        association = self.request.user.association
        serializer.save(association=association)

class ProofVerificationView(APIView):
    def post(self, request):
        proof_file = request.FILES.get('proof')
        if not proof_file:
            return Response({"error": "Proof file is required."}, status=status.HTTP_400_BAD_REQUEST)   
        verification_service = VerificationService(proof_file)
        if verification_service.verify_proof():
            return Response({"message": "Proof verified successfully.", "verified": True}, status=status.HTTP_200_OK)
        return Response({"error": "Proof verification failed.", "verified": False}, status=status.HTTP_400_BAD_REQUEST)

class TransactionCreateView(APIView):
    permission_classes = [AllowAny]
    serializer = TransactionSerializer

    def post(self, request):
        data = request.data
        assoc_short_name = data.get('association_short_name')
        payer_data = data.get('payer')
        if isinstance(payer_data, str):
            payer_data = json.loads(payer_data)
            
        payment_item_ids = request.data.get('payment_item_ids')
        if isinstance(payment_item_ids, str):
            payment_item_ids = json.loads(payment_item_ids)
            
        amount_paid = data.get('amount_paid')
        proof_file = request.FILES.get('proof_of_payment')

        try:
            association = Association.objects.get(association_short_name=assoc_short_name)
        except Association.DoesNotExist:
            return Response({"error": "Association not found."}, status=status.HTTP_404_NOT_FOUND)
        
        payer, _ = Payer.objects.get_or_create(
            association=association,
            matric_number=payer_data['matricNumber'],
            defaults={
                'first_name': payer_data['firstName'],
                'last_name': payer_data['lastName'],
                'email': payer_data['email'],
                'phone_number': payer_data.get('phoneNumber', ''),
                'faculty': payer_data.get('faculty', ''),
                'department': payer_data.get('department', ''),
            }
        )

        transaction = Transaction.objects.create(
            payer=payer,
            association=association,
            amount_paid=amount_paid,
            proof_of_payment=proof_file
        )
        transaction.payment_items.set(PaymentItem.objects.filter(id__in=payment_item_ids))
        transaction.save()

        return Response({'success': True, 'transaction_id': transaction.id}, status=201)