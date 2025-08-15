import hmac
import hashlib
import json
import logging
import requests
import re
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings

KORAPAY_BASE_URL = "https://api.korapay.com/merchant/api/v1"
logger = logging.getLogger(__name__)

def get_webhook_secret() -> str:
    return getattr(settings, 'KORAPAY_WEBHOOK_SECRET', None) or getattr(settings, 'KORAPAY_SECRET_KEY', '')

def compute_signature(raw: bytes, secret: str) -> str:
    return hmac.new(secret.encode('utf-8'), raw, hashlib.sha256).hexdigest()

def is_valid_signature(raw_body: bytes, header_signature: str) -> bool:
    secret = get_webhook_secret()
    if not secret or not header_signature:
        return False
    expected = compute_signature(raw_body, secret)
    if hmac.compare_digest(expected, header_signature):
        return True
    try:
        payload = json.loads(raw_body.decode('utf-8'))
        data_part = payload.get('data')
        if data_part is not None:
            data_json = json.dumps(data_part, separators=(',', ':')).encode('utf-8')
            expected2 = compute_signature(data_json, secret)
            if hmac.compare_digest(expected2, header_signature):
                return True
    except Exception:
        pass
    return False

def _format_amount_2dp(amount: str | Decimal) -> str:
    d = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{d:.2f}"

def _sanitize_customer_name(name: str) -> str:
    if not name:
        return "DuesPay User"
    name = re.sub(r"<[^>]*>", "", name)
    name = re.sub(r"&[A-Za-z]+;", "", name)
    name = re.sub(r"[^A-Za-z0-9\s\.\,'\-]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "DuesPay User"

def _amount_number(amount: str | Decimal):
    d = Decimal(str(amount)).quantize(Decimal("0.01"))
    # Send int if whole number, else float with 2dp
    return int(d) if d == d.to_integral() else float(d)

def korapay_init_charge(*, amount: str, currency: str, reference: str, customer: dict, redirect_url: str) -> dict:
    url = f"{KORAPAY_BASE_URL}/charges/initialize"
    headers = {
        "Authorization": f"Bearer {getattr(settings, 'KORAPAY_SECRET_KEY', '')}",
        "Content-Type": "application/json",
    }

    email = customer.get("email") or ""
    if "@" not in email:
        email = getattr(settings, "DEFAULT_PAYMENTS_EMAIL", "payments@duespay.app")
    raw_name = customer.get("name") or "DuesPay User"
    name = _sanitize_customer_name(raw_name)

    if not str(redirect_url).startswith("https://"):
        # Dev-only fallback; Korapay prefers https
        redirect_url = "http://localhost:5173/payment/callback"

    payload = {
        "amount": _format_amount_2dp(amount),
        "currency": currency,
        "reference": reference,
        "redirect_url": redirect_url,
        "customer": {"name": name, "email": email},
        "metadata": {"txn_ref": reference},
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if not resp.ok:
        try:
            body = resp.json()
        except Exception:
            body = {"text": resp.text}
        logger.error(f"Korapay init 4xx/5xx: status={resp.status_code} body={body}")
        resp.raise_for_status()
    return resp.json()

def korapay_payout_bank(*, amount: str, bank_code: str, account_number: str, reference: str, narration: str, customer: dict) -> dict:
    """
    Initiate a payout to a bank account using Korapay disburse API.
    """
    endpoint = getattr(settings, "KORAPAY_PAYOUT_PATH", "/transactions/disburse")
    url = f"{KORAPAY_BASE_URL.rstrip('/')}{endpoint}"
    headers = {
        "Authorization": f"Bearer {getattr(settings, 'KORAPAY_SECRET_KEY', '')}",
        "Content-Type": "application/json",
    }

    bank = str(bank_code or "").strip()
    acct = str(account_number or "").strip()
    cust_name = _sanitize_customer_name((customer or {}).get("name") or "Association")
    cust_email = (customer or {}).get("email") or "finance@duespay.app"

    payload = {
        "reference": reference,
        "destination": {
            "type": "bank_account",
            "amount": _amount_number(amount),
            "currency": "NGN",
            "narration": (narration or "")[:80],
            "bank_account": {
                "bank": bank,
                "account": acct,
            },
            "customer": {
                "name": cust_name,
                "email": cust_email,
            },
        },
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    try:
        data = resp.json()
    except Exception:
        data = {"text": resp.text}

    if resp.status_code in (200, 201):
        logger.info(f"Korapay payout ok ref={reference} resp={data}")
        return data

    # Idempotency tolerance for duplicate references
    duplicate = False
    try:
        code = (data.get("code") or "").lower()
        msg = (data.get("message") or "").lower()
        duplicate = "duplicate" in code or "duplicate" in msg or "reference has already been used" in msg
    except Exception:
        pass
    if duplicate:
        logger.info(f"Korapay payout duplicate (idempotent) ref={reference} resp={data}")
        return data

    logger.error(f"Korapay payout failed status={resp.status_code} resp={data}")
    resp.raise_for_status()
    return data