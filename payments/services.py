import requests
from django.conf import settings
from django.core.cache import cache
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def _ts():
    return datetime.now(timezone.utc).isoformat()

class VerifyBankService:
    """
    Kept name for backward compatibility, now powered by Korapay.
    """
    BASE_URL = getattr(settings, "KORAPAY_BASE_URL", "https://api.korapay.com/merchant/api/v1")
    HEADERS = {
        # Korapay requires PUBLIC key for these misc endpoints
        "Authorization": f"Bearer {getattr(settings, 'KORAPAY_PUBLIC_KEY', '')}",
        "Content-Type": "application/json",
    }
    BANK_LIST_CACHE_KEY = "korapay_bank_list"
    BANK_LIST_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

    @staticmethod
    def get_bank_list():
        """
        Fetch list of Nigerian banks and their codes from Korapay.
        Returns a list of { name, code } dicts (same shape as before).
        """
        print(f"[{_ts()}] [BANKS] Fetching bank list...")
        cached_banks = cache.get(VerifyBankService.BANK_LIST_CACHE_KEY)
        if cached_banks:
            logger.info(f"[{_ts()}][BANKS] Using cached banks count={len(cached_banks)}")
            print(f"[{_ts()}] [BANKS] Cached banks: {len(cached_banks)}")
            return cached_banks

        # Fallback list (same as before) in case Korapay is unreachable
        fallback_banks = [
            {"name": "Access Bank", "code": "044"},
            {"name": "Zenith Bank", "code": "057"},
            {"name": "GTBank", "code": "058"},
            {"name": "First Bank", "code": "011"},
            {"name": "UBA", "code": "033"},
            {"name": "Fidelity Bank", "code": "070"},
            {"name": "FCMB", "code": "214"},
            {"name": "Stanbic IBTC Bank", "code": "221"},
            {"name": "Sterling Bank", "code": "232"},
            {"name": "Unity Bank", "code": "215"},
            {"name": "Test Bank", "code": "100004"},
        ]

        url = f"{VerifyBankService.BASE_URL.rstrip('/')}/misc/banks"
        params = {"countryCode": "NG"}
        try:
            resp = requests.get(url, headers=VerifyBankService.HEADERS, params=params, timeout=15)
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if not resp.ok or not data.get("status"):
                logger.error(f"[{_ts()}][BANKS][ERR] status={resp.status_code} body={data}")
                print(f"[{_ts()}] [BANKS][ERR] status={resp.status_code}")
                raise RuntimeError("Korapay bank list error")

            banks_raw = data.get("data") or []
            # Map to {name, code} for frontend compatibility
            banks = [{"name": b.get("name"), "code": b.get("code")} for b in banks_raw if b.get("name") and b.get("code")]
            cache.set(VerifyBankService.BANK_LIST_CACHE_KEY, banks, VerifyBankService.BANK_LIST_CACHE_TIMEOUT)
            logger.info(f"[{_ts()}][BANKS][OK] fetched={len(banks)}")
            print(f"[{_ts()}] [BANKS][OK] fetched={len(banks)}")
            return banks
        except Exception as e:
            logger.error(f"[{_ts()}][BANKS][EXC] {e}", exc_info=True)
            print(f"[{_ts()}] [BANKS] Using fallback banks: {len(fallback_banks)}")
            return fallback_banks

    @staticmethod
    def verify_account(account_number, bank_code):
        """
        Verify bank account using Korapay.
        Returns dict with keys: account_name, bank_name, account_number, bank_code (same shape used by the view).
        """
        print(f"[{_ts()}] [VERIFY] acct={account_number} bank={bank_code}")
        url = f"{VerifyBankService.BASE_URL.rstrip('/')}/misc/banks/resolve/"
        payload = {"bank": str(bank_code), "account": str(account_number)}

        try:
            resp = requests.post(url, headers=VerifyBankService.HEADERS, json=payload, timeout=20)
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if not resp.ok or not data.get("status"):
                logger.error(f"[{_ts()}][VERIFY][ERR] status={resp.status_code} body={data}")
                print(f"[{_ts()}] [VERIFY][ERR] status={resp.status_code}")
                return None

            d = data.get("data") or {}
            if d.get("account_name"):
                result = {
                    "account_name": d.get("account_name"),
                    "first_name": "",     # kept for compatibility; not provided by Korapay
                    "last_name": "",
                    "other_name": "",
                    "account_number": d.get("account_number"),
                    "bank_code": d.get("bank_code") or bank_code,
                    "bank_name": d.get("bank_name"),
                }
                logger.info(f"[{_ts()}][VERIFY][OK] acct={result['account_number']} bank={result['bank_code']}")
                print(f"[{_ts()}] [VERIFY][OK] acct={result['account_number']}")
                return result

            logger.warning(f"[{_ts()}][VERIFY] No account_name in response: {data}")
            return None
        except Exception as e:
            logger.error(f"[{_ts()}][VERIFY][EXC] {e}", exc_info=True)
            return None

