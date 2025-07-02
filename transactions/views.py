import json
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from django.db import models
from rest_framework.permissions import IsAuthenticated, AllowAny
from .services import VerificationService
from .models import Transaction
from association.models import Association
from payers.services import PayerService
from payments.models import PaymentItem, ReceiverBankAccount
from .serializers import TransactionSerializer, ProofAndTransactionSerializer

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

       
        total_collections = queryset.aggregate(total=models.Sum('amount_paid'))['total'] or 0

        # Completed Payments (assuming is_verified=True means completed)
        completed_count = queryset.filter(is_verified=True).count()

        # Pending Payments (assuming is_verified=False means pending)
        pending_count = queryset.filter(is_verified=False).count()

        percent_collections = "+12%" 
        percent_completed = "+8%"    
        percent_pending = "-2%"      

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


class ProofAndTransactionView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProofAndTransactionSerializer

    def post(self, request):

        # raise Exception("Intentional server error for testing")

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        assoc_short_name = data['association_short_name']
        payer_data = data['payer']
        payment_item_ids = data['payment_item_ids']
        amount_paid = data['amount_paid']
        proof_file = data['proof_file']

        try:
            association = Association.objects.get(association_short_name=assoc_short_name)
        except Association.DoesNotExist:
            return Response({"error": "Association not found."}, status=status.HTTP_404_NOT_FOUND)

        payment_items = PaymentItem.objects.filter(id__in=payment_item_ids)
        if payment_items.count() != len(payment_item_ids):
            return Response({"error": "One or more payment items not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bank_account = ReceiverBankAccount.objects.get(association=association)
        except ReceiverBankAccount.DoesNotExist:
            return Response({"error": "Bank account not found for association."}, status=status.HTTP_404_NOT_FOUND)

        # Verification
        verifier = VerificationService(proof_file, amount_paid, payment_items, bank_account)
        verified, message = verifier.verify_proof()
        if not verified:
            return Response({"verified": False, "error": message}, status=status.HTTP_400_BAD_REQUEST)

        # Payer logic
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

        # Create transaction
        transaction = Transaction.objects.create(
            payer=payer,
            association=association,
            amount_paid=amount_paid,
            proof_of_payment=proof_file,
            is_verified=False
        )
        transaction.payment_items.set(payment_items)
        transaction.save()

        # Prepare items paid for
        items_paid = [
            {
                "id": item.id,
                "title": item.title,
                "amount": item.amount,
                "status": item.status,
            }
            for item in payment_items
        ]

        return Response({
            'success': True,
            'transaction_id': transaction.id,
            'reference_id': transaction.reference_id,
            'items_paid': items_paid,
        }, status=201)
    