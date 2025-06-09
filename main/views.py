import json
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import models
from rest_framework.permissions import IsAuthenticated, AllowAny
from .services import VerificationService, PayerService
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import AdminUserSerializer, CustomTokenObtainPairSerializer, PayerCheckSerializer, PayerSerializer
from .models import (
    Association, PaymentItem, ReceiverBankAccount, Payer,
    TransactionReceipt, Transaction, AdminUser
)
from .serializers import (
    AssociationSerializer, PaymentItemSerializer, 
    RegisterSerializer, TransactionSerializer, 
    ReceiverBankAccountSerializer
)

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

    def perform_create(self, serializer):
        association = self.request.user.association
        serializer.save(association=association)

    def get_queryset(self):
        association = getattr(self.request.user, 'association', None)
        queryset = PaymentItem.objects.none()
        if association:
            queryset = PaymentItem.objects.filter(association=association)

        # Search by title
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)

        # Filter by is_active (status)
        status = self.request.query_params.get('status')
        if status is not None:
            if status.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif status.lower() == 'false':
                queryset = queryset.filter(is_active=False)

        # Filter by type (status field: 'optional' or 'compulsory')
        type_param = self.request.query_params.get('type')
        if type_param:
            queryset = queryset.filter(status__iexact=type_param)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if not queryset.exists():
            return Response({"results": [], "count": 0, "message": "No payment items found."})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
        
class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        association = getattr(self.request.user, 'association', None)
        queryset = Transaction.objects.none()
        if association:
            queryset = Transaction.objects.filter(association=association)

        # Filter by verification status
        status_param = self.request.query_params.get('status')
        if status_param is not None:
            if status_param.lower() == 'verified':
                queryset = queryset.filter(is_verified=True)
            elif status_param.lower() == 'unverified':
                queryset = queryset.filter(is_verified=False)

        # Search by payer name or reference id
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(reference_id__icontains=search) |
                models.Q(payer__first_name__icontains=search) |
                models.Q(payer__last_name__icontains=search) |
                models.Q(payer__matric_number__icontains=search)
            )

        return queryset

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

    def get_queryset(self):
        association = getattr(self.request.user, 'association', None)
        if association:
            return ReceiverBankAccount.objects.filter(association=association)
        return ReceiverBankAccount.objects.none()

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
        
        payer, error = PayerService.check_or_update_payer(
            association,
            payer_data['matricNumber'],
            payer_data['email'],
            payer_data.get('phoneNumber', ''),
            payer_data['firstName'],
            payer_data['lastName'],
            payer_data.get('faculty', ''),
            payer_data.get('department', '')
        )
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        transaction = Transaction.objects.create(
            payer=payer,
            association=association,
            amount_paid=amount_paid,
            proof_of_payment=proof_file
        )
        transaction.payment_items.set(PaymentItem.objects.filter(id__in=payment_item_ids))
        transaction.save()

        return Response({'success': True, 'transaction_id': transaction.id}, status=201)
    
class PayerCheckView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PayerCheckSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data

        assoc_short_name = data.get('association_short_name')
        try:
            association = Association.objects.get(association_short_name=assoc_short_name)
        except Association.DoesNotExist:
            return Response({"error": "Association not found."}, status=status.HTTP_404_NOT_FOUND)

        payer, error = PayerService.check_or_update_payer(
            association,
            data['matric_number'],
            data['email'],
            data['phone_number'],
            data['first_name'],
            data['last_name'],
            data.get('faculty', ''),
            data.get('department', '')
        )
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "success": True,
            "payer_id": payer.id,
            "message": "Payer found or updated successfully."
        }, status=200)
    
class PayerViewSet(viewsets.ModelViewSet):
    queryset = Payer.objects.all()
    serializer_class = PayerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        association = getattr(self.request.user, 'association', None)
        queryset = Payer.objects.none()
        if association:
            queryset = Payer.objects.filter(association=association)

        # Search by name, matric number, email, faculty, department
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(matric_number__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(faculty__icontains=search) |
                models.Q(department__icontains=search)
            )

        # Filter by faculty
        faculty = self.request.query_params.get('faculty')
        if faculty:
            queryset = queryset.filter(faculty__iexact=faculty)

        # Filter by department
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department__iexact=department)

        return queryset

    def perform_create(self, serializer):
        serializer.save(association=self.request.user.association)
        
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)