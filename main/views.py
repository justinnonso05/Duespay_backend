import json
import hmac
import hashlib
import logging
from decimal import Decimal, InvalidOperation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated  # added IsAuthenticated
from rest_framework import generics  # added
from rest_framework_simplejwt.views import TokenObtainPairView  # added
from django.shortcuts import redirect  # added
from django.contrib.auth.tokens import default_token_generator  # added
from django.template.loader import render_to_string  # added
from django.core.mail import EmailMultiAlternatives  # added
from transactions.models import Transaction
from payers.models import Payer
from association.models import Association, Session
from payments.models import PaymentItem, ReceiverBankAccount  # add ReceiverBankAccount
from django.conf import settings
from .services import is_valid_signature, korapay_init_charge, korapay_payout_bank
# import logging, json  # removed duplicate imports
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from datetime import timedelta
from .models import PlatformVBA, AdminUser
from .serializers import (
    AdminUserSerializer, 
    CustomTokenObtainPairSerializer, 
    RegisterSerializer, 
    PasswordResetRequestSerializer, 
    PasswordResetConfirmSerializer
)

logger = logging.getLogger(__name__)

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

class InitiatePaymentView(APIView):
    """
    Initiates Korapay hosted checkout for a payer and selected items.
    Expected JSON:
    {
      "payer_id": int,
      "association_id": int,
      "session_id": int,
      "payment_item_ids": [int, ...],
      "amount": "optional string - must equal computed total if provided",
      "payer_name": "optional",
      "payer_email": "optional"
    }
    Returns: { reference_id, amount, checkout_url }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        required = ["payer_id", "association_id", "session_id", "payment_item_ids"]
        missing = [k for k in required if k not in data]
        if missing:
            return Response({"error": f"Missing fields: {', '.join(missing)}"}, status=400)

        # Load entities
        try:
            payer = Payer.objects.get(pk=data["payer_id"])
            association = Association.objects.get(pk=data["association_id"])
            session = Session.objects.get(pk=data["session_id"], association=association)
        except (Payer.DoesNotExist, Association.DoesNotExist, Session.DoesNotExist):
            return Response({"error": "Invalid payer_id, association_id, or session_id"}, status=400)

        # Validate items belong to association/session
        item_ids = data.get("payment_item_ids") or []
        if not isinstance(item_ids, list) or not item_ids:
            return Response({"error": "payment_item_ids must be a non-empty list"}, status=400)

        items_qs = PaymentItem.objects.filter(id__in=item_ids, session=session)
        if items_qs.count() != len(set(item_ids)):
            return Response({"error": "One or more payment items not found for the session"}, status=400)

        # Compute total amount from items
        total = sum((item.amount for item in items_qs), Decimal("0.00"))

        # Optional amount check
        # client_amount = data.get("amount")
        # if client_amount is not None:
        #     try:
        #         client_amount_dec = Decimal(str(client_amount))
        #     except (InvalidOperation, ValueError):
        #         return Response({"error": "Invalid amount format"}, status=400)
        #     if client_amount_dec != total:
                # return Response({"error": "Amount mismatch with selected items"}, status=400)

        amount = total

        # Create pending transaction
        txn = Transaction.objects.create(
            payer=payer,
            association=association,
            amount_paid=amount,  # expected amount
            is_verified=False,
            session=session,
        )
        txn.payment_items.set(items_qs)

        # Prepare Korapay checkout
        full_name = (data.get("payer_name")
                     or f"{payer.first_name} {payer.last_name}".strip())
        email = (data.get("payer_email")
                 or payer.email
                 or "payments@duespay.app")
        customer = {
            "name": full_name,
            "email": email,
        }
        frontend = getattr(settings, "KORAPAY_REDIRECT_URL", None) or getattr(settings, "FRONTEND_URL", "https://duespay.vercel.app")
        redirect_url = f"{frontend.rstrip('/')}/payment/callback"

        try:
            korapay_res = korapay_init_charge(
                amount=str(amount),
                currency="NGN",
                reference=txn.reference_id,  # your merchant ref
                customer=customer,
                redirect_url=redirect_url,
            )
        except Exception as e:
            logger.exception("Korapay init charge failed")
            return Response({"error": "Failed to initialize payment"}, status=502)

        data_obj = korapay_res.get("data") or {}
        checkout_url = data_obj.get("checkout_url") or data_obj.get("authorization_url")
        if not checkout_url:
            return Response({"error": "Korapay did not return a checkout URL", "provider_response": korapay_res}, status=502)

        return Response(
            {"reference_id": txn.reference_id, "amount": str(amount), "checkout_url": checkout_url},
            status=201,
        )

@csrf_exempt
@require_http_methods(["POST"])
def korapay_webhook(request):
    """
    Verifies Korapay signature, resolves transaction by merchant reference,
    and marks it verified. Handles provider ref fallback gracefully.
    """
    signature = request.headers.get("x-korapay-signature") or request.headers.get("X-KoraPay-Signature")
    if not is_valid_signature(request.body, signature):
        logger.warning("Korapay webhook signature invalid")
        return HttpResponseForbidden()

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponse(status=200)

    if payload.get("event") != "charge.success":
        return HttpResponse(status=200)

    data = payload.get("data") or {}

    # Candidate refs: try merchant reference first
    candidates = []
    for key in ("transaction_reference", "reference", "order_reference"):
        val = data.get(key)
        if val:
            candidates.append(val)
    meta = data.get("metadata") or {}
    for key in ("txn_ref", "reference", "transaction_reference", "order_ref"):
        val = meta.get(key)
        if val:
            candidates.append(val)

    txn = None
    for ref in candidates:
        try:
            txn = Transaction.objects.get(reference_id=ref)
            break
        except Transaction.DoesNotExist:
            continue

    if not txn:
        logger.warning(f"Korapay webhook: no Transaction match for refs={candidates}")
        return HttpResponse(status=200)  # ack to avoid retries

    if txn.is_verified:
        return HttpResponse(status=200)

    amt = data.get("amount")
    try:
        if amt is not None:
            txn.amount_paid = Decimal(str(amt))
    except Exception:
        pass

    txn.is_verified = True
    txn.save(update_fields=["amount_paid", "is_verified"])
    logger.info(f"Transaction {txn.reference_id} verified via Korapay hosted checkout")

    # Attempt auto-payout to association
    try:
        rcv = ReceiverBankAccount.objects.filter(association=txn.association).first()
        if not rcv:
            logger.warning(f"Payout skipped: no ReceiverBankAccount for association {txn.association_id}")
        else:
            payout_ref = f"{txn.reference_id}-OUT"[:40]  # ensure within provider limits
            narration = f"Dues payout {txn.reference_id}"
            assoc = txn.association
            assoc_name = getattr(assoc, "association_name", None) or getattr(assoc, "association_short_name", None) or str(assoc)
            assoc_email = "finance@duespay.app"  # Association model has no email field
            korapay_payout_bank(
                amount=str(txn.amount_paid),
                bank_code=getattr(rcv, "bank_code", ""),
                account_number=getattr(rcv, "account_number", ""),
                reference=payout_ref,
                narration=narration,
                customer={"name": assoc_name, "email": assoc_email},
            )
    except Exception:
        logger.exception(f"Payout attempt failed for txn {txn.reference_id}")
    return HttpResponse(status=200)

class PaymentStatusView(APIView):
    """
    Simple polling endpoint for frontend after redirect.
    GET /payment/status/<reference_id>/
    """
    permission_classes = [AllowAny]

    def get(self, request, reference_id: str):
        try:
            txn = Transaction.objects.select_related("payer", "association", "session").get(reference_id=reference_id)
        except Transaction.DoesNotExist:
            return Response({"exists": False}, status=200)

        receipt = getattr(txn, "receipt", None)
        payload = {
            "exists": True,
            "reference_id": txn.reference_id,
            "is_verified": txn.is_verified,
            "amount_paid": str(txn.amount_paid),
            "receipt_id": getattr(receipt, "receipt_id", None),
        }
        return Response(payload, status=200)
