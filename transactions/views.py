import json
import logging
from decimal import Decimal
from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from association.models import Association, Session
from payers.models import Payer
from payments.models import PaymentItem, ReceiverBankAccount
from transactions.models import Transaction

from .chargeServices import is_valid_signature, korapay_init_bank_transfer, korapay_init_charge, korapay_payout_bank
from .models import Transaction, TransactionReceipt
from .serializers import TransactionReceiptDetailSerializer, TransactionSerializer

logger = logging.getLogger(__name__)

class TransactionPagination(PageNumberPagination):
    page_size = 7  
    page_size_query_param = 'page_size'  
    max_page_size = 1000

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TransactionPagination

    def get_queryset(self):
        association = getattr(self.request.user, "association", None)
        queryset = Transaction.objects.none()

        if association:
            # Get session_id from query params or use current session
            session_id = self.request.query_params.get("session_id")

            if session_id:
                # Validate that session belongs to this association
                try:
                    session = Session.objects.get(
                        id=session_id, association=association
                    )
                    queryset = Transaction.objects.filter(session=session)
                except Session.DoesNotExist:
                    queryset = Transaction.objects.none()
            elif association.current_session:
                # Use current session if no session_id provided
                queryset = Transaction.objects.filter(
                    session=association.current_session
                )
            else:
                # No session available, return empty queryset
                queryset = Transaction.objects.none()

        # Filter by verification status (case-insensitive)
        status_param = self.request.query_params.get("status")
        if status_param is not None:
            if status_param.lower() == "verified":
                queryset = queryset.filter(is_verified=True)
            elif status_param.lower() == "unverified":
                queryset = queryset.filter(is_verified=False)

        # Search by payer name or reference id (case-insensitive)
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(reference_id__icontains=search)
                | models.Q(payer__first_name__icontains=search)
                | models.Q(payer__last_name__icontains=search)
                | models.Q(payer__matric_number__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        association = getattr(self.request.user, "association", None)
        if not association or not association.current_session:
            raise ValidationError(
                "No current session available. Please create a session first."
            )

        serializer.save(
            payer=self.request.user.payer,
            association=association,
            session=association.current_session,  # Auto-assign current session
        )

    def list(self, request, *args, **kwargs):
        # Check if association has a current session
        association = getattr(self.request.user, "association", None)
        if not association:
            return Response(
                {"error": "No association found for user"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_id = self.request.query_params.get("session_id")
        current_session = None

        if session_id:
            try:
                current_session = Session.objects.get(
                    id=session_id, association=association
                )
            except Session.DoesNotExist:
                return Response(
                    {
                        "error": "Session not found or does not belong to your association"
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        elif association.current_session:
            current_session = association.current_session
        else:
            return Response(
                {
                    "error": "No session available. Please create a session first.",
                    "results": [],
                    "count": 0,
                    "next": None,
                    "previous": None,
                    "meta": {
                        "total_collections": 0,
                        "completed_payments": 0,
                        "pending_payments": 0,
                        "total_transactions": 0,
                        "percent_collections": "-",
                        "percent_completed": "-",
                        "percent_pending": "-",
                        "current_session": None,
                    },
                }
            )

        queryset = self.filter_queryset(self.get_queryset()).order_by("-submitted_at")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        total_collections = (
            queryset.aggregate(total=models.Sum("amount_paid"))["total"] or 0
        )

        # Completed Payments (assuming is_verified=True means completed)
        completed_count = queryset.filter(is_verified=True).count()

        # Pending Payments (assuming is_verified=False means pending)
        pending_count = queryset.filter(is_verified=False).count()

        # Calculate percentages
        total_count = queryset.count()
        percent_completed = (
            round((completed_count / total_count * 100), 1) if total_count > 0 else 0
        )
        percent_pending = (
            round((pending_count / total_count * 100), 1) if total_count > 0 else 0
        )

        meta = {
            "total_collections": float(total_collections),
            "completed_payments": completed_count,
            "pending_payments": pending_count,
            "total_transactions": total_count,
            "percent_collections": "-",  # You can calculate this based on your business logic
            "percent_completed": f"{percent_completed}%",
            "percent_pending": f"{percent_pending}%",
            "current_session": (
                {
                    "id": current_session.id,
                    "title": current_session.title,
                    "start_date": current_session.start_date,
                    "end_date": current_session.end_date,
                    "is_active": current_session.is_active,
                }
                if current_session
                else None
            ),
        }

        if page is not None:
            paginated_response = self.get_paginated_response(data)
            response_data = paginated_response.data
            response_data["meta"] = meta
            return Response(response_data)
        else:
            return Response(
                {
                    "results": data,
                    "count": len(data),
                    "next": None,
                    "previous": None,
                    "meta": meta,
                }
            )


class TransactionReceiptDetailView(RetrieveAPIView):
    queryset = TransactionReceipt.objects.select_related(
        "transaction__payer", "transaction__association", "transaction__session"
    ).prefetch_related("transaction__payment_items")
    serializer_class = TransactionReceiptDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "receipt_id"


class InitiatePaymentView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        required = ["payer_id", "association_id", "session_id", "payment_item_ids"]
        missing = [k for k in required if k not in data]
        if missing:
            return Response(
                {"error": f"Missing fields: {', '.join(missing)}"}, status=400
            )

        try:
            payer = Payer.objects.get(pk=data["payer_id"])
            association = Association.objects.get(pk=data["association_id"])
            session = Session.objects.get(
                pk=data["session_id"], association=association
            )
        except (Payer.DoesNotExist, Association.DoesNotExist, Session.DoesNotExist):
            return Response(
                {"error": "Invalid payer_id, association_id, or session_id"}, status=400
            )

        item_ids = data.get("payment_item_ids") or []
        if not isinstance(item_ids, list) or not item_ids:
            return Response(
                {"error": "payment_item_ids must be a non-empty list"}, status=400
            )
        items_qs = PaymentItem.objects.filter(id__in=item_ids, session=session)
        if items_qs.count() != len(set(item_ids)):
            return Response(
                {"error": "One or more payment items not found for the session"},
                status=400,
            )

        # Base total (DB), add platform fee to charge only
        base_total = sum((item.amount for item in items_qs), Decimal("0.00"))
        platform_fee = Decimal(str(getattr(settings, "PLATFORM_PAYOUT_FEE_NGN", "100.00")))
        platform_percent = Decimal(str(getattr(settings, "PLATFORM_PAYIN_PERCENT", "0.015")))
        charge_amount = base_total + platform_fee + (base_total * platform_percent)

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
        source = str(
            getattr(settings, "KORAPAY_CHARGE_CUSTOMER_SOURCE", "payer")
        ).lower()
        platform_name = getattr(settings, "PLATFORM_NAME", "Duespay")
        platform_email = getattr(settings, "PLATFORM_EMAIL", "justondev05@gmail.com")

        if source == "platform":
            full_name = platform_name
            email = platform_email
        elif source == "association":
            assoc_name = (
                getattr(association, "association_name", None)
                or getattr(association, "association_short_name", None)
                or str(association)
            )
            admin_email = getattr(
                getattr(association, "adminuser", None), "email", None
            ) or getattr(getattr(association, "admin", None), "email", None)
            full_name = assoc_name
            email = admin_email or platform_email
        else:
            full_name = (
                data.get("payer_name")
                or f"{getattr(payer, 'first_name', '')} {getattr(payer, 'last_name', '')}"
            ).strip() or "DuesPay User"
            email = (
                data.get("payer_email")
                or getattr(payer, "email", None)
                or platform_email
            )
        if "@" not in str(email):
            email = platform_email
        customer = {"name": full_name, "email": email}

        # Frontend redirect with association info
        frontend = getattr(settings, "KORAPAY_REDIRECT_URL", None) or getattr(
            settings, "FRONTEND_URL", "https://duespay.vercel.app"
        )
        redirect_url = f"{str(frontend).rstrip('/')}/payment/callback?assoc={association.association_short_name}"
        

        # Metadata for reconciliation
        metadata = {
            "txn_ref": txn.reference_id,
            "platform_fee": str(platform_fee),
            "base_amount": str(base_total),
            "association_id": association.id,
            "payer_id": payer.id,
        }

        logger.info(
            f"[INITIATE] ref={txn.reference_id} base={base_total} fee={platform_fee} charge={charge_amount} customer={customer} redirect={redirect_url}"
        )
        print(
            f"[{timezone.now().isoformat()}] INITIATE ref={txn.reference_id} base={base_total} fee={platform_fee} charge={charge_amount}"
        )

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
            logger.exception(
                f"[INITIATE][ERROR] ref={txn.reference_id} Korapay init failed"
            )
            return Response({"error": "Failed to initialize payment"}, status=502)

        data_obj = korapay_res.get("data") or {}
        checkout_url = data_obj.get("checkout_url") or data_obj.get("authorization_url")
        if not checkout_url:
            logger.error(
                f"[INITIATE][ERROR] ref={txn.reference_id} Missing checkout_url resp={korapay_res}"
            )
            return Response(
                {
                    "error": "Korapay did not return a checkout URL",
                    "provider_response": korapay_res,
                },
                status=502,
            )

        logger.info(
            f"[INITIATE][OK] ref={txn.reference_id} checkout_url={checkout_url}"
        )
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


class InitiateBankTransferView(APIView):
    """
    Create bank transfer payment with dynamic virtual account.
    Customer bears the transaction cost.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or {}
        required = ["payer_id", "association_id", "session_id", "payment_item_ids"]
        missing = [k for k in required if k not in data]
        if missing:
            return Response(
                {"success": False, "message": f"Missing fields: {', '.join(missing)}"}, status=400
            )

        try:
            payer = Payer.objects.get(pk=data["payer_id"])
            association = Association.objects.get(pk=data["association_id"])
            session = Session.objects.get(
                pk=data["session_id"], association=association
            )
        except (Payer.DoesNotExist, Association.DoesNotExist, Session.DoesNotExist):
            return Response(
                {"success": False, "message": "Invalid payer_id, association_id, or session_id"}, status=400
            )

        item_ids = data.get("payment_item_ids") or []
        if not isinstance(item_ids, list) or not item_ids:
            return Response(
                {"success": False, "message": "payment_item_ids must be a non-empty list"}, status=400
            )
        items_qs = PaymentItem.objects.filter(id__in=item_ids, session=session)
        if items_qs.count() != len(set(item_ids)):
            return Response(
                {"success": False, "message": "One or more payment items not found for the session"},
                status=400,
            )

        # Calculate base total (what association receives)
        base_total = sum((item.amount for item in items_qs), Decimal("0.00"))
        
        # Optional: Platform fees (placeholders - customer bears Korapay fees)
        platform_fee = Decimal(str(getattr(settings, "PLATFORM_PAYOUT_FEE_NGN", "0.00")))  # Placeholder
        platform_percent = Decimal(str(getattr(settings, "PLATFORM_PAYIN_PERCENT", "0.00")))  # Placeholder
        
        # For bank transfer, customer bears Korapay fees, so charge amount = base amount
        charge_amount = base_total + platform_fee + (base_total * platform_percent)

        # Create pending transaction
        txn = Transaction.objects.create(
            payer=payer,
            association=association,
            amount_paid=base_total,  # Store base amount (what association gets)
            is_verified=False,
            session=session,
        )
        txn.payment_items.set(items_qs)

        # Customer details - Use payer data from backend (removed client-side overrides)
        full_name = f"{getattr(payer, 'first_name', '')} {getattr(payer, 'last_name', '')}".strip() or "DuesPay User"
        email = getattr(payer, "email", None) or getattr(settings, "PLATFORM_EMAIL", "justondev05@gmail.com")
        
        # Ensure valid email format
        if "@" not in str(email):
            email = getattr(settings, "PLATFORM_EMAIL", "justondev05@gmail.com")
        
        customer = {"name": full_name, "email": email}

        # Notification URL (webhook)
        notification_url = getattr(settings, "KORAPAY_WEBHOOK_URL", None)
        if not notification_url:
            # Construct from current domain if not set
            base_url = getattr(settings, "BACKEND_URL", "https://duespay.onrender.com")
            notification_url = f"{base_url.rstrip('/')}/api/transactions/webhook/"

        # Account name for the virtual account
        account_name = f"{association.association_short_name}-checkout"  # Keep reasonable length

        # Narration
        narration = f"Dues payment for {association.association_short_name}"

        # Metadata for reconciliation
        metadata = {
            "txn_ref": txn.reference_id,
            "assoc_id": str(association.id),
            "payer_id": str(payer.id),
            "base_amount": str(base_total),
        }

        logger.info(
            f"[BANK_TRANSFER] ref={txn.reference_id} base={base_total} charge={charge_amount} customer={customer}"
        )

        try:
            korapay_res = korapay_init_bank_transfer(
                amount=str(base_total),
                currency="NGN",
                reference=txn.reference_id,
                customer=customer,
                # notification_url=notification_url,
                account_name=account_name,
                narration=narration,
                metadata=metadata,
                merchant_bears_cost=False,  # Customer bears cost
            )
        except Exception as e:
            logger.exception(
                f"[BANK_TRANSFER][ERROR] ref={txn.reference_id} Korapay init failed: {e}"
            )
            return Response({
                "success": False, 
                "message": "Failed to initialize bank transfer payment"
            }, status=502)

        # Extract response data
        if not korapay_res.get("status"):
            logger.error(
                f"[BANK_TRANSFER][ERROR] ref={txn.reference_id} Korapay error: {korapay_res}"
            )
            return Response({
                "success": False,
                "message": korapay_res.get("message", "Bank transfer initialization failed"),
                "provider_response": korapay_res,
            }, status=502)

        data_obj = korapay_res.get("data", {})
        bank_account = data_obj.get("bank_account", {})
        amount_with_fee = float(base_total) + float(data_obj.get("fee", 0)) + float(data_obj.get("vat", 0))
        
        # Calculate expiry time in seconds
        expiry_seconds = None
        expiry_date_str = bank_account.get("expiry_date_in_utc")
        if expiry_date_str:
            try:
                expiry_date = parse_datetime(expiry_date_str)
                if expiry_date:
                    now = datetime.now(expiry_date.tzinfo)
                    expiry_seconds = int((expiry_date - now).total_seconds())
                    expiry_seconds = max(0, expiry_seconds)  # Ensure non-negative
            except Exception as e:
                logger.warning(f"[BANK_TRANSFER] Failed to parse expiry date: {e}")

        logger.info(
            f"[BANK_TRANSFER][OK] ref={txn.reference_id} account={bank_account.get('account_number')} bank={bank_account.get('bank_name')}"
        )

        return Response({
            "success": True,
            "message": "Bank transfer payment initiated successfully",
            "data": {
                "reference_id": txn.reference_id,
                "amount": str(base_total),
                "total_payable": str(amount_with_fee),
                "currency": data_obj.get("currency", "NGN"),
                "amount_expected": data_obj.get("amount_expected"),
                "fee": data_obj.get("fee"),
                "vat": data_obj.get("vat"),
                "status": data_obj.get("status", "processing"),
                "bank_account": {
                    "account_name": bank_account.get("account_name"),
                    "account_number": bank_account.get("account_number"),
                    "bank_name": bank_account.get("bank_name"),
                    "bank_code": bank_account.get("bank_code"),
                    "expiry_date_in_utc": bank_account.get("expiry_date_in_utc"),
                    "expiry_seconds": expiry_seconds,
                },
                "customer": data_obj.get("customer"),
                "narration": data_obj.get("narration"),
            }
        }, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def korapay_webhook(request):
    """
    Verifies Korapay signature, resolves transaction by merchant reference,
    and marks it verified. Handles provider ref fallback gracefully.
    """
    signature = request.headers.get("x-korapay-signature") or request.headers.get(
        "X-KoraPay-Signature"
    )
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
        logger.warning(
            f"[WEBHOOK] base_amount derive failed ref={txn.reference_id} amt={amt} meta={meta}"
        )

    # Keep DB amount as base amount (exclude fee)
    if base_amount is not None:
        if txn.amount_paid != base_amount:
            logger.info(
                f"[WEBHOOK] reconciling amount ref={txn.reference_id} db={txn.amount_paid} -> base={base_amount}"
            )
            txn.amount_paid = base_amount
    # else: leave txn.amount_paid as created (base_total)

    txn.is_verified = True
    txn.save(update_fields=["amount_paid", "is_verified"])
    logger.info(f"[WEBHOOK][VERIFIED] ref={txn.reference_id} amount={txn.amount_paid}")
    print(
        f"[{timezone.now().isoformat()}] VERIFIED ref={txn.reference_id} amount={txn.amount_paid}"
    )

    # Auto-payout (immediate). Optional "bulk for halls" switch, default immediate.
    # try:
    #     # Decide if association is a hall
    #     assoc = txn.association
    #     assoc_type = (
    #         getattr(assoc, "association_type", None)
    #         or getattr(assoc, "type", None)
    #         or getattr(assoc, "category", None)
    #     )
    #     is_hall = str(assoc_type or "").lower() == "hall"

    #     use_bulk_for_halls = bool(
    #         getattr(settings, "KORAPAY_USE_BULK_FOR_HALLS", False)
    #     )
    #     if is_hall and use_bulk_for_halls:
    #         logger.info(
    #             f"[PAYOUT][SKIP-NOQUEUE] Hall association detected (id={assoc.id}). Configure a queue/worker to batch payouts."
    #         )
    #         print(
    #             f"[{timezone.now().isoformat()}] PAYOUT skipped for hall (bulk mode on). ref={txn.reference_id}"
    #         )
    #         return HttpResponse(status=200)

    #     # Immediate payout path
    #     rcv = ReceiverBankAccount.objects.filter(association=assoc).first()
    #     if not rcv:
    #         logger.warning(
    #             f"[PAYOUT][SKIP] no ReceiverBankAccount assoc_id={assoc.id} ref={txn.reference_id}"
    #         )
    #         print(
    #             f"[{timezone.now().isoformat()}] PAYOUT skipped (no bank) ref={txn.reference_id}"
    #         )
    #         return HttpResponse(status=200)

    #     payout_ref = f"{txn.reference_id}-OUT"[:40]  # idempotent
    #     narration = f"Dues payout {txn.reference_id}"[:80]
    #     assoc_name = (
    #         getattr(assoc, "association_name", None)
    #         or getattr(assoc, "association_short_name", None)
    #         or str(assoc)
    #     )
    #     assoc_email = (
    #         getattr(getattr(assoc, "adminuser", None), "email", None)
    #         or getattr(getattr(assoc, "admin", None), "email", None)
    #         or getattr(settings, "PLATFORM_EMAIL", "justondev05@gmail.com")
    #     )

    #     logger.info(
    #         f"[PAYOUT][START] ref={payout_ref} bank={getattr(rcv,'bank_code',None)} acct={getattr(rcv,'account_number',None)} amount={txn.amount_paid} assoc_id={assoc.id}"
    #     )
    #     print(
    #         f"[{timezone.now().isoformat()}] PAYOUT START ref={payout_ref} amount={txn.amount_paid}"
    #     )

    #     korapay_payout_bank(
    #         amount=str(txn.amount_paid),
    #         bank_code=getattr(rcv, "bank_code", ""),
    #         account_number=getattr(rcv, "account_number", ""),
    #         reference=payout_ref,
    #         narration=narration,
    #         customer={"name": assoc_name, "email": assoc_email},
    #     )

    #     logger.info(f"[PAYOUT][END] ref={payout_ref} ok")
    #     print(f"[{timezone.now().isoformat()}] PAYOUT OK ref={payout_ref}")

    # except Exception:
    #     logger.exception(f"[PAYOUT][ERROR] ref={txn.reference_id}")
    #     print(f"[{timezone.now().isoformat()}] PAYOUT ERROR ref={txn.reference_id}")
    return HttpResponse(status=200)


class PaymentStatusView(APIView):
    """
    Simple polling endpoint for frontend after redirect.
    """

    permission_classes = [AllowAny]

    def get(self, request, reference_id: str):
        try:
            txn = Transaction.objects.select_related(
                "payer", "association", "session"
            ).get(reference_id=reference_id)
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
