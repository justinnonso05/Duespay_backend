import hashlib
import hmac
import json
import logging
import re
from datetime import datetime
from datetime import timezone as dt_tz
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.conf import settings

KORAPAY_BASE_URL = getattr(
    settings, "KORAPAY_BASE_URL", "https://api.korapay.com/merchant/api/v1"
)
logger = logging.getLogger(__name__)


def _ts():
    return datetime.now(dt_tz.utc).isoformat()


def get_webhook_secret() -> str:
    return getattr(settings, "KORAPAY_WEBHOOK_SECRET", None) or getattr(
        settings, "KORAPAY_SECRET_KEY", ""
    )


def compute_signature(raw: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def is_valid_signature(raw_body: bytes, header_signature: str) -> bool:
    secret = get_webhook_secret()
    if not secret or not header_signature:
        return False
    expected = compute_signature(raw_body, secret)
    if hmac.compare_digest(expected, header_signature):
        return True
    try:
        payload = json.loads(raw_body.decode("utf-8"))
        data_part = payload.get("data")
        if data_part is not None:
            data_json = json.dumps(data_part, separators=(",", ":")).encode("utf-8")
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
    return int(d) if d == d.to_integral() else float(d)


def korapay_init_charge(
    *,
    amount: str,
    currency: str,
    reference: str,
    customer: dict,
    redirect_url: str,
    metadata: dict | None = None,
) -> dict:
    url = f"{KORAPAY_BASE_URL}/charges/initialize"
    headers = {
        "Authorization": f"Bearer {getattr(settings, 'KORAPAY_SECRET_KEY', '')}",
        "Content-Type": "application/json",
    }

    platform_name = getattr(settings, "PLATFORM_NAME", "Duespay")
    platform_email = getattr(settings, "PLATFORM_EMAIL", "justondev05@gmail.com")

    email = (customer or {}).get("email") or platform_email
    if "@" not in str(email):
        email = platform_email
    raw_name = (customer or {}).get("name") or platform_name
    name = _sanitize_customer_name(raw_name)

    if not str(redirect_url).startswith("https://"):
        if getattr(settings, "DEBUG", False):
            logger.debug(
                f"[{_ts()}] Using non-HTTPS redirect_url in DEBUG: {redirect_url}"
            )
        else:
            raise ValueError("redirect_url must be https in production")

    meta = {"txn_ref": reference}
    if isinstance(metadata, dict):
        try:
            # ensure simple JSON-serializable values
            meta.update(
                {
                    k: (str(v) if isinstance(v, (Decimal,)) else v)
                    for k, v in metadata.items()
                }
            )
        except Exception:
            meta.update(metadata)

    payload = {
        "amount": _format_amount_2dp(amount),
        "currency": currency,
        "reference": reference,
        "redirect_url": redirect_url,
        "customer": {"name": name, "email": email},
        "metadata": meta,
    }

    logger.info(
        f"[{_ts()}][CHARGE][REQ] ref={reference} amount={payload['amount']} email={email} meta={meta}"
    )
    print(
        f"[{_ts()}] CHARGE REQ ref={reference} amount={payload['amount']} email={email}"
    )

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    try:
        body = resp.json()
    except Exception:
        body = {"text": resp.text}

    if not resp.ok:
        logger.error(
            f"[{_ts()}][CHARGE][ERR] ref={reference} status={resp.status_code} body={body}"
        )
        print(f"[{_ts()}] CHARGE ERR ref={reference} status={resp.status_code}")
        resp.raise_for_status()

    logger.info(f"[{_ts()}][CHARGE][OK] ref={reference} status={resp.status_code}")
    print(f"[{_ts()}] CHARGE OK ref={reference} status={resp.status_code}")
    return body


def korapay_payout_bank(
    *,
    amount: str,
    bank_code: str,
    account_number: str,
    reference: str,
    narration: str,
    customer: dict,
) -> dict:
    url = f"{KORAPAY_BASE_URL}/transactions/disburse"
    headers = {
        "Authorization": f"Bearer {getattr(settings, 'KORAPAY_SECRET_KEY', '')}",
        "Content-Type": "application/json",
    }

    # Validations to prevent bad disbursements
    try:
        amt_num = _amount_number(amount)
        if isinstance(amt_num, (int, float)) and amt_num <= 0:
            raise ValueError("Amount must be > 0")
    except Exception as e:
        logger.error(
            f"[{_ts()}][PAYOUT][VALIDATION] bad amount={amount} ref={reference} err={e}"
        )
        raise

    bank = str(bank_code or "").strip()
    acct = str(account_number or "").strip()
    if not bank.isdigit() or len(bank) < 3:
        raise ValueError(f"Invalid bank code: {bank}")
    if not acct.isdigit() or len(acct) != 10:
        raise ValueError(f"Invalid account number: {acct}")

    cust_name = _sanitize_customer_name((customer or {}).get("name") or "Association")
    cust_email = (customer or {}).get("email") or "finance@duespay.app"

    payload = {
        "reference": reference,
        "destination": {
            "type": "bank_account",
            "amount": amt_num,
            "currency": "NGN",
            "narration": (narration or "")[:80],
            "bank_account": {"bank": bank, "account": acct},
            "customer": {"name": cust_name, "email": cust_email},
        },
    }

    logger.info(
        f"[{_ts()}][PAYOUT][REQ] ref={reference} amount={amt_num} bank={bank} acct={acct}"
    )
    print(
        f"[{_ts()}] PAYOUT REQ ref={reference} amount={amt_num} bank={bank} acct={acct}"
    )

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    try:
        data = resp.json()
    except Exception:
        data = {"text": resp.text}

    if resp.status_code in (200, 201):
        logger.info(f"[{_ts()}][PAYOUT][OK] ref={reference} resp={data}")
        print(f"[{_ts()}] PAYOUT OK ref={reference}")
        return data

    # Idempotency: treat duplicate reference as OK
    duplicate = False
    try:
        code = (data.get("code") or "").lower()
        msg = (data.get("message") or "").lower()
        duplicate = (
            "duplicate" in code
            or "duplicate" in msg
            or "reference has already been used" in msg
        )
    except Exception:
        pass
    if duplicate:
        logger.info(f"[{_ts()}][PAYOUT][DUP] ref={reference} resp={data}")
        print(f"[{_ts()}] PAYOUT DUP ref={reference}")
        return data

    logger.error(
        f"[{_ts()}][PAYOUT][ERR] ref={reference} status={resp.status_code} resp={data}"
    )
    print(f"[{_ts()}] PAYOUT ERR ref={reference} status={resp.status_code}")
    resp.raise_for_status()
    return data


def korapay_init_bank_transfer(
    *,
    amount: str,
    currency: str,
    reference: str,
    customer: dict,
    notification_url: str = None,
    account_name: str = None,
    narration: str = None,
    metadata: dict | None = None,
    merchant_bears_cost: bool = False,
) -> dict:
    """
    Create Korapay bank transfer payment with dynamic virtual account.
    Customer bears cost by default (merchant_bears_cost=False).
    """
    url = f"{KORAPAY_BASE_URL}/charges/bank-transfer"
    headers = {
        "Authorization": f"Bearer {getattr(settings, 'KORAPAY_SECRET_KEY', '')}",
        "Content-Type": "application/json",
    }

    platform_name = getattr(settings, "PLATFORM_NAME", "Duespay")
    platform_email = getattr(settings, "PLATFORM_EMAIL", "justondev05@gmail.com")

    email = (customer or {}).get("email") or platform_email
    if "@" not in str(email):
        email = platform_email
    raw_name = (customer or {}).get("name") or platform_name
    name = _sanitize_customer_name(raw_name)

    # Prepare metadata
    meta = {"txn_ref": reference}
    if isinstance(metadata, dict):
        try:
            # Ensure simple JSON-serializable values (max 5 fields per Korapay docs)
            filtered_meta = {}
            for k, v in metadata.items():
                if len(filtered_meta) >= 5:  # Korapay limit
                    break
                key = str(k)[:20]  # Max 20 chars per field name
                value = str(v) if isinstance(v, (Decimal,)) else v
                filtered_meta[key] = value
            meta.update(filtered_meta)
        except Exception:
            if metadata:
                meta.update(metadata)

    payload = {
        "reference": reference,
        "amount": _amount_number(amount),
        "currency": currency,
        "customer": {"name": name, "email": email},
        "merchant_bears_cost": merchant_bears_cost,
    }

    # Optional fields
    if notification_url:
        payload["notification_url"] = notification_url
    if account_name:
        payload["account_name"] = account_name
    if narration:
        payload["narration"] = narration[:80]  # Reasonable limit
    if meta:
        payload["metadata"] = meta

    logger.info(
        f"[{_ts()}][BANK_TRANSFER][REQ] ref={reference} amount={payload['amount']} email={email} merchant_bears_cost={merchant_bears_cost}"
    )
    print(
        f"[{_ts()}] BANK_TRANSFER REQ ref={reference} amount={payload['amount']} email={email}"
    )

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    try:
        body = resp.json()
    except Exception:
        body = {"text": resp.text}

    if not resp.ok:
        logger.error(
            f"[{_ts()}][BANK_TRANSFER][ERR] ref={reference} status={resp.status_code} body={body}"
        )
        print(f"[{_ts()}] BANK_TRANSFER ERR ref={reference} status={resp.status_code}")
        resp.raise_for_status()

    logger.info(f"[{_ts()}][BANK_TRANSFER][OK] ref={reference} status={resp.status_code}")
    print(f"[{_ts()}] BANK_TRANSFER OK ref={reference} status={resp.status_code}")
    return body
