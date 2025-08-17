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
from payments.models import PaymentItem, ReceiverBankAccount
from django.conf import settings
from .services import is_valid_signature, korapay_init_charge, korapay_payout_bank
# import logging, json  # removed duplicate imports
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework_simplejwt.tokens import RefreshToken
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


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("id_token")

        try:
            # Verify token with Google
            idinfo = id_token.verify_oauth2_token(
                token, requests.Request(), settings.GOOGLE_CLIENT_ID
            )

            email = idinfo["email"]
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")

            # Check if user exists
            user, created = AdminUser.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "auth_mode": "google",
                }
            )

            # If the user was created, mark first login
            if created:
                user.is_first_login = True
                user.save()
            else:
                # If existing user registered with email but tries google login → allow since emails match
                if user.auth_mode == "email":
                    pass  
                elif user.auth_mode != "google":
                    return Response({"error": "Invalid auth mode"}, status=400)

            # Issue tokens
            refresh = RefreshToken.for_user(user)

            # Set is_first_login to False after first login
            was_first_login = user.is_first_login
            if was_first_login:
                user.is_first_login = False
                user.save(update_fields=["is_first_login"])

            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "is_first_login": was_first_login,
                "auth_mode": user.auth_mode,
            })

        except ValueError:
            return Response({"error": "Invalid Google token"}, status=400)


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
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        required = ["payer_id", "association_id", "session_id", "payment_item_ids"]
        missing = [k for k in required if k not in data]
        if missing:
            return Response({"error": f"Missing fields: {', '.join(missing)}"}, status=400)

        try:
            payer = Payer.objects.get(pk=data["payer_id"])
            association = Association.objects.get(pk=data["association_id"])
            session = Session.objects.get(pk=data["session_id"], association=association)
        except (Payer.DoesNotExist, Association.DoesNotExist, Session.DoesNotExist):
            return Response({"error": "Invalid payer_id, association_id, or session_id"}, status=400)

        item_ids = data.get("payment_item_ids") or []
        if not isinstance(item_ids, list) or not item_ids:
            return Response({"error": "payment_item_ids must be a non-empty list"}, status=400)
        items_qs = PaymentItem.objects.filter(id__in=item_ids, session=session)
        if items_qs.count() != len(set(item_ids)):
            return Response({"error": "One or more payment items not found for the session"}, status=400)

        # Base total (DB), add platform fee to charge only
        base_total = sum((item.amount for item in items_qs), Decimal("0.00"))
        platform_fee = Decimal(str(getattr(settings, "PLATFORM_FEE_NGN", "100.00")))
        charge_amount = base_total + platform_fee

        # Create pending transaction with base amount only (exclude fee)
        txn = Transaction.objects.create(
            payer=payer,
            association=association,
            amount_paid=base_total,
            is_verified=False,
            session=session,
        )
        txn.payment_items.set(items_qs)

        # Customer mapping (payer/platform/association)
        source = str(getattr(settings, "KORAPAY_CHARGE_CUSTOMER_SOURCE", "payer")).lower()
        platform_name = getattr(settings, "PLATFORM_NAME", "Duespay")
        platform_email = getattr(settings, "PLATFORM_EMAIL", "justondev05@gmail.com")

        if source == "platform":
            full_name = platform_name
            email = platform_email
        elif source == "association":
            assoc_name = getattr(association, "association_name", None) or getattr(association, "association_short_name", None) or str(association)
            admin_email = getattr(getattr(association, "adminuser", None), "email", None) or getattr(getattr(association, "admin", None), "email", None)
            full_name = assoc_name
            email = admin_email or platform_email
        else:
            full_name = (data.get("payer_name") or f"{getattr(payer, 'first_name', '')} {getattr(payer, 'last_name', '')}").strip() or "DuesPay User"
            email = data.get("payer_email") or getattr(payer, "email", None) or platform_email
        if "@" not in str(email):
            email = platform_email
        customer = {"name": full_name, "email": email}

        # Frontend redirect
        frontend = getattr(settings, "KORAPAY_REDIRECT_URL", None) or getattr(settings, "FRONTEND_URL", "https://duespay.vercel.app")
        redirect_url = f"{str(frontend).rstrip('/')}/payment/callback"

        # Metadata for reconciliation
        metadata = {
            "txn_ref": txn.reference_id,
            "platform_fee": str(platform_fee),
            "base_amount": str(base_total),
            "association_id": association.id,
            "payer_id": payer.id,
        }

        logger.info(f"[INITIATE] ref={txn.reference_id} base={base_total} fee={platform_fee} charge={charge_amount} customer={customer} redirect={redirect_url}")
        print(f"[{timezone.now().isoformat()}] INITIATE ref={txn.reference_id} base={base_total} fee={platform_fee} charge={charge_amount}")

        try:
            korapay_res = korapay_init_charge(
                amount=str(charge_amount),
                currency="NGN",
                reference=txn.reference_id,
                customer=customer,
                redirect_url=redirect_url,
                metadata=metadata,  # NEW
            )
        except Exception:
            logger.exception(f"[INITIATE][ERROR] ref={txn.reference_id} Korapay init failed")
            return Response({"error": "Failed to initialize payment"}, status=502)

        data_obj = korapay_res.get("data") or {}
        checkout_url = data_obj.get("checkout_url") or data_obj.get("authorization_url")
        if not checkout_url:
            logger.error(f"[INITIATE][ERROR] ref={txn.reference_id} Missing checkout_url resp={korapay_res}")
            return Response({"error": "Korapay did not return a checkout URL", "provider_response": korapay_res}, status=502)

        logger.info(f"[INITIATE][OK] ref={txn.reference_id} checkout_url={checkout_url}")
        # Return both base and gross for UI clarity (amount kept for backward compatibility)
        return Response(
            {
                "reference_id": txn.reference_id,
                "amount": str(base_total),
                "platform_fee": str(platform_fee),
                "total_payable": str(charge_amount),
                "checkout_url": checkout_url,
            },
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
        logger.warning("[WEBHOOK] invalid signature")
        return HttpResponseForbidden()

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        logger.error("[WEBHOOK] invalid JSON")
        return HttpResponse(status=200)

    event = payload.get("event")
    data = payload.get("data") or {}
    logger.info(f"[WEBHOOK] event={event} data_keys={list(data.keys())}")
    print(f"[{timezone.now().isoformat()}] WEBHOOK event={event}")

    if event != "charge.success":
        return HttpResponse(status=200)

    # Resolve transaction by merchant reference preference
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
        logger.warning(f"[WEBHOOK] no Transaction match for refs={candidates}")
        return HttpResponse(status=200)

    if txn.is_verified:
        logger.info(f"[WEBHOOK] already verified ref={txn.reference_id}")
        return HttpResponse(status=200)

    meta = data.get("metadata") or {}
    amt = data.get("amount")
    base_amount = None
    try:
        if "base_amount" in meta:
            base_amount = Decimal(str(meta.get("base_amount")))
        elif amt is not None and "platform_fee" in meta:
            base_amount = Decimal(str(amt)) - Decimal(str(meta.get("platform_fee")))
    except Exception:
        logger.warning(f"[WEBHOOK] base_amount derive failed ref={txn.reference_id} amt={amt} meta={meta}")

    # Keep DB amount as base amount (exclude fee)
    if base_amount is not None:
        if txn.amount_paid != base_amount:
            logger.info(f"[WEBHOOK] reconciling amount ref={txn.reference_id} db={txn.amount_paid} -> base={base_amount}")
            txn.amount_paid = base_amount
    # else: leave txn.amount_paid as created (base_total)

    txn.is_verified = True
    txn.save(update_fields=["amount_paid", "is_verified"])
    logger.info(f"[WEBHOOK][VERIFIED] ref={txn.reference_id} amount={txn.amount_paid}")
    print(f"[{timezone.now().isoformat()}] VERIFIED ref={txn.reference_id} amount={txn.amount_paid}")

    # Auto-payout (immediate). Optional "bulk for halls" switch, default immediate.
    try:
        # Decide if association is a hall
        assoc = txn.association
        assoc_type = (
            getattr(assoc, "association_type", None)
            or getattr(assoc, "type", None)
            or getattr(assoc, "category", None)
        )
        is_hall = str(assoc_type or "").lower() == "hall"

        use_bulk_for_halls = bool(getattr(settings, "KORAPAY_USE_BULK_FOR_HALLS", False))
        if is_hall and use_bulk_for_halls:
            logger.info(f"[PAYOUT][SKIP-NOQUEUE] Hall association detected (id={assoc.id}). Configure a queue/worker to batch payouts.")
            print(f"[{timezone.now().isoformat()}] PAYOUT skipped for hall (bulk mode on). ref={txn.reference_id}")
            return HttpResponse(status=200)

        # Immediate payout path
        rcv = ReceiverBankAccount.objects.filter(association=assoc).first()
        if not rcv:
            logger.warning(f"[PAYOUT][SKIP] no ReceiverBankAccount assoc_id={assoc.id} ref={txn.reference_id}")
            print(f"[{timezone.now().isoformat()}] PAYOUT skipped (no bank) ref={txn.reference_id}")
            return HttpResponse(status=200)

        payout_ref = f"{txn.reference_id}-OUT"[:40]  # idempotent
        narration = f"Dues payout {txn.reference_id}"[:80]
        assoc_name = getattr(assoc, "association_name", None) or getattr(assoc, "association_short_name", None) or str(assoc)
        assoc_email = getattr(getattr(assoc, "adminuser", None), "email", None) or getattr(getattr(assoc, "admin", None), "email", None) or getattr(settings, "PLATFORM_EMAIL", "justondev05@gmail.com")

        logger.info(f"[PAYOUT][START] ref={payout_ref} bank={getattr(rcv,'bank_code',None)} acct={getattr(rcv,'account_number',None)} amount={txn.amount_paid} assoc_id={assoc.id}")
        print(f"[{timezone.now().isoformat()}] PAYOUT START ref={payout_ref} amount={txn.amount_paid}")

        korapay_payout_bank(
            amount=str(txn.amount_paid),
            bank_code=getattr(rcv, "bank_code", ""),
            account_number=getattr(rcv, "account_number", ""),
            reference=payout_ref,
            narration=narration,
            customer={"name": assoc_name, "email": assoc_email},
        )

        logger.info(f"[PAYOUT][END] ref={payout_ref} ok")
        print(f"[{timezone.now().isoformat()}] PAYOUT OK ref={payout_ref}")

    except Exception:
        logger.exception(f"[PAYOUT][ERROR] ref={txn.reference_id}")
        print(f"[{timezone.now().isoformat()}] PAYOUT ERROR ref={txn.reference_id}")
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
