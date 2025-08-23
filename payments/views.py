from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import PaymentItem, ReceiverBankAccount
from .serializers import (
    PaymentItemSerializer, 
    ReceiverBankAccountSerializer, 
    BankAccountVerificationSerializer,
    BankListSerializer,  # Add this import
    BankVerificationResponseSerializer  # Add this import
)
from association.models import Session
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from .services import VerifyBankService, FlutterwaveBankService
import logging

logger = logging.getLogger(__name__)


class PaymentItemViewSet(viewsets.ModelViewSet):
    queryset = PaymentItem.objects.all()
    serializer_class = PaymentItemSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        association = getattr(self.request.user, 'association', None)
        if not association or not association.current_session:
            raise ValidationError("No current session available. Please create a session first.")
        
        serializer.save(
            association=association,
            session=association.current_session
        )

    def get_queryset(self):
        association = getattr(self.request.user, 'association', None)
        queryset = PaymentItem.objects.none()
        
        if association:
            session_id = self.request.query_params.get('session_id')
            
            if session_id:
                try:
                    session = Session.objects.get(id=session_id, association=association)
                    queryset = PaymentItem.objects.filter(session=session)
                except Session.DoesNotExist:
                    queryset = PaymentItem.objects.none()
            elif association.current_session:
                queryset = PaymentItem.objects.filter(session=association.current_session)

        # Search by title
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)

        # Filter by is_active
        status_filter = self.request.query_params.get('status')
        if status_filter is not None:
            if status_filter.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif status_filter.lower() == 'false':
                queryset = queryset.filter(is_active=False)

        # Filter by type (compulsory/optional)
        type_param = self.request.query_params.get('type')
        if type_param:
            queryset = queryset.filter(status__iexact=type_param)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if not queryset.exists():
            return Response({"results": [], "count": 0, "message": "No payment items found."})
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ReceiverBankAccountViewSet(viewsets.ModelViewSet):
    queryset = ReceiverBankAccount.objects.all()
    serializer_class = ReceiverBankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            association = self.request.user.association
            return ReceiverBankAccount.objects.filter(association=association)
        except AttributeError:
            return ReceiverBankAccount.objects.none()

    def perform_create(self, serializer):
        try:
            association = self.request.user.association
        except AttributeError:
            raise ValidationError("User has no associated association.")
        
        if ReceiverBankAccount.objects.filter(association=association).exists():
            raise ValidationError("Bank account already exists for this association.")
        
        # Mark as verified when saving through this endpoint
        serializer.save(association=association, is_verified=True)

    def list(self, request, *args, **kwargs):
        """Get the current user's bank account"""
        try:
            association = request.user.association
            try:
                bank_account = association.bank_account
                serializer = self.get_serializer(bank_account)
                return Response({
                    "success": True,
                    "data": serializer.data
                })
            except ReceiverBankAccount.DoesNotExist:
                return Response({
                    "success": True,
                    "data": None,
                    "message": "No bank account found"
                })
        except AttributeError:
            return Response(
                {"success": False, "message": "User has no association"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        """Create a new bank account"""
        try:
            association = request.user.association
        except AttributeError:
            return Response({
                "success": False,
                "message": "User has no association"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if bank account already exists
        if ReceiverBankAccount.objects.filter(association=association).exists():
            return Response({
                "success": False,
                "message": "Bank account already exists for this association."
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(association=association, is_verified=True)
            return Response({
                "success": True,
                "message": "Bank account saved successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "success": False,
                "message": "Invalid data",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update existing bank account"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save(is_verified=True)  # Keep as verified
            return Response({
                "success": True,
                "message": "Bank account updated successfully",
                "data": serializer.data
            })
        else:
            return Response({
                "success": False,
                "message": "Invalid data",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Delete bank account"""
        instance = self.get_object()
        instance.delete()
        return Response({
            "success": True,
            "message": "Bank account deleted successfully"
        }, status=status.HTTP_204_NO_CONTENT)


class BankListView(APIView):
    """Get list of Nigerian banks from provider"""
    permission_classes = [AllowAny]

    def get(self, request):
        provider = request.query_params.get("provider", "korapay").lower()
        if provider == "flutterwave":
            # Call Flutterwave service and normalize
            try:
                fw_resp = FlutterwaveBankService.get_bank_list()
                # Flutterwave: {"status": "success", "message": "...", "data": [banks]}
                banks = [
                    {"name": b.get("name"), "code": b.get("code")}
                    for b in (fw_resp.get("data") or [])
                    if b.get("name") and b.get("code")
                ]
            except Exception as e:
                logger.error(f"[BANKS][API] Flutterwave error: {e}")
                banks = []
        else:
            banks = VerifyBankService.get_bank_list()

        if not banks:
            logger.error("[BANKS][API] Could not retrieve bank list at the moment.")
            return Response(
                {"status": "error", "message": "Could not retrieve bank list at the moment.", "banks": []},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        return Response({"status": "success", "banks": banks})

class VerifyBankAccountView(APIView):
    """Verify bank account details only - NO SAVING"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logger.info(f"[BANK_VERIFY][API] Verification request from user: {request.user}")
        logger.info(f"[BANK_VERIFY][API] Request data: {request.data}")

        try:
            try:
                association = request.user.association
                logger.info(f"[BANK_VERIFY][API] User association found: {association}")
            except AttributeError:
                logger.error("[BANK_VERIFY][API] User has no association")
                return Response({
                    "success": False,
                    "message": "User is not associated with any association.",
                    "errors": {"user": ["No association found"]}
                }, status=status.HTTP_400_BAD_REQUEST)

            serializer = BankAccountVerificationSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"[BANK_VERIFY][API] Validation errors: {serializer.errors}")
                return Response({
                    "success": False,
                    "message": "Validation failed",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            account_number = serializer.validated_data['account_number']
            bank_code = serializer.validated_data['bank_code']
            provider = request.query_params.get("provider", "korapay").lower()
            logger.info(f"[BANK_VERIFY][API] Attempting to verify: {account_number} with bank code: {bank_code} via {provider}")

            if provider == "flutterwave":
                fw_resp = FlutterwaveBankService.verify_account(account_number, bank_code)
                if fw_resp and fw_resp.get("status") == "success" and fw_resp.get("data"):
                    data = fw_resp["data"]
                    # Lookup bank name using bank_code
                    banks_resp = FlutterwaveBankService.get_bank_list()
                    banks = banks_resp.get("data", []) if isinstance(banks_resp, dict) else banks_resp
                    bank_name = ""
                    for b in banks:
                        if b.get("code") == data.get("bank_code", bank_code):
                            bank_name = b.get("name", "")
                            break
                    verification_data = {
                        "account_name": data.get("account_name", ""),
                        "bank_name": bank_name,
                        "account_number": data.get("account_number", account_number),
                        "bank_code": data.get("bank_code", bank_code),
                        "verified": True
                    }
                    return Response({
                        "success": True,
                        "message": fw_resp.get("message", "Bank account verified successfully"),
                        "data": verification_data
                    })
                else:
                    fail_message = fw_resp.get("message", "Bank account verification failed. Please check your details.") if fw_resp else "Bank account verification failed."
                    return Response({
                        "success": False,
                        "message": fail_message,
                        "errors": {"verification": [fail_message]}
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                verification_data = VerifyBankService.verify_account(account_number, bank_code)
                if not verification_data:
                    return Response({
                        "success": False,
                        "message": "Bank account verification failed. Please check your details.",
                        "errors": {"verification": ["Invalid account details"]}
                    }, status=status.HTTP_400_BAD_REQUEST)
                return Response({
                    "success": True,
                    "message": "Bank account verified successfully",
                    "data": {
                        "account_name": verification_data.get('account_name', ''),
                        "bank_name": verification_data.get('bank_name', ''),
                        "account_number": verification_data.get('account_number', account_number),
                        "bank_code": verification_data.get('bank_code', bank_code),
                        "verified": True
                    }
                })

        except Exception as e:
            logger.error(f"[BANK_VERIFY][API] Unexpected error: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": "An unexpected error occurred",
                "errors": {"general": [str(e)]}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
