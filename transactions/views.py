import json
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from django.db import models
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from .services import VerificationService
from .models import Transaction, TransactionReceipt
from association.models import Association, Session
from payers.services import PayerService
from payments.models import PaymentItem, ReceiverBankAccount
from .serializers import TransactionSerializer, ProofAndTransactionSerializer, TransactionReceiptDetailSerializer
from rest_framework.generics import RetrieveAPIView
from rest_framework.exceptions import ValidationError

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        association = getattr(self.request.user, 'association', None)
        queryset = Transaction.objects.none()
        
        if association:
            # Get session_id from query params or use current session
            session_id = self.request.query_params.get('session_id')
            
            if session_id:
                # Validate that session belongs to this association
                try:
                    session = Session.objects.get(id=session_id, association=association)
                    queryset = Transaction.objects.filter(session=session)
                except Session.DoesNotExist:
                    queryset = Transaction.objects.none()
            elif association.current_session:
                # Use current session if no session_id provided
                queryset = Transaction.objects.filter(session=association.current_session)
            else:
                # No session available, return empty queryset
                queryset = Transaction.objects.none()

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
        association = getattr(self.request.user, 'association', None)
        if not association or not association.current_session:
            raise ValidationError("No current session available. Please create a session first.")
        
        serializer.save(
            payer=self.request.user.payer,
            association=association,
            session=association.current_session  # Auto-assign current session
        )

    def list(self, request, *args, **kwargs):
        # Check if association has a current session
        association = getattr(self.request.user, 'association', None)
        if not association:
            return Response({'error': 'No association found for user'}, status=status.HTTP_400_BAD_REQUEST)
        
        session_id = self.request.query_params.get('session_id')
        current_session = None
        
        if session_id:
            try:
                current_session = Session.objects.get(id=session_id, association=association)
            except Session.DoesNotExist:
                return Response({'error': 'Session not found or does not belong to your association'}, status=status.HTTP_404_NOT_FOUND)
        elif association.current_session:
            current_session = association.current_session
        else:
            return Response({
                'error': 'No session available. Please create a session first.',
                'results': [],
                'count': 0,
                'next': None,
                'previous': None,
                'meta': {
                    'total_collections': 0,
                    'completed_payments': 0,
                    'pending_payments': 0,
                    'total_transactions': 0,
                    'percent_collections': '-',
                    'percent_completed': '-',
                    'percent_pending': '-',
                    'current_session': None
                }
            })

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

        # Calculate percentages
        total_count = queryset.count()
        percent_completed = round((completed_count / total_count * 100), 1) if total_count > 0 else 0
        percent_pending = round((pending_count / total_count * 100), 1) if total_count > 0 else 0

        meta = {
            "total_collections": float(total_collections),
            "completed_payments": completed_count,
            "pending_payments": pending_count,
            "total_transactions": total_count,
            "percent_collections": "-",  # You can calculate this based on your business logic
            "percent_completed": f"{percent_completed}%",
            "percent_pending": f"{percent_pending}%",
            "current_session": {
                "id": current_session.id,
                "title": current_session.title,
                "start_date": current_session.start_date,
                "end_date": current_session.end_date,
                "is_active": current_session.is_active
            } if current_session else None
        }

        if page is not None:
            paginated_response = self.get_paginated_response(data)
            response_data = paginated_response.data
            response_data['meta'] = meta
            return Response(response_data)
        else:
            return Response({
                'results': data,
                'count': len(data),
                'next': None,
                'previous': None,
                'meta': meta
            })


class ProofAndTransactionView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProofAndTransactionSerializer

    def post(self, request):
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

        # Check if association has a current session
        if not association.current_session:
            return Response({
                "error": "Association has no active session. Please contact the association admin."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Filter payment items by current session
        payment_items = PaymentItem.objects.filter(id__in=payment_item_ids, session=association.current_session)
        if payment_items.count() != len(payment_item_ids):
            return Response({"error": "One or more payment items not found in current session."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bank_account = ReceiverBankAccount.objects.get(association=association)
        except ReceiverBankAccount.DoesNotExist:
            return Response({"error": "Bank account not found for association."}, status=status.HTTP_404_NOT_FOUND)
        
        # Verification
        verifier = VerificationService(proof_file, amount_paid, payment_items, bank_account)
        verified, message = verifier.verify_proof()
        if not verified:
            return Response({"verified": False, "error": message}, status=status.HTTP_400_BAD_REQUEST)

        # Payer logic - check if payer exists in current session
        payer, error = PayerService.check_or_update_payer(
            association,
            association.current_session,  # Pass session instance
            payer_data['matricNumber'],
            payer_data['email'],
            payer_data['phoneNumber'],
            payer_data['firstName'],
            payer_data['lastName'],
            payer_data.get('faculty', ''),
            payer_data.get('department', '')
        )
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        # Create transaction with session
        transaction = Transaction.objects.create(
            payer=payer,
            association=association,
            session=association.current_session,  # Add session
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

class TransactionReceiptDetailView(RetrieveAPIView):
    queryset = TransactionReceipt.objects.select_related(
        'transaction__payer', 'transaction__association', 'transaction__session'
    ).prefetch_related('transaction__payment_items')
    serializer_class = TransactionReceiptDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'receipt_id'

