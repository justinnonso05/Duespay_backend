import requests
from django.conf import settings
from django.core.cache import cache
import logging
from datetime import datetime, timezone
import time

logger = logging.getLogger(__name__)

class VerifyBankService:
    """
    Korapay-powered bank list and account verification.
    """
    BASE_URL = getattr(settings, "KORAPAY_BASE_URL", "https://api.korapay.com/merchant/api/v1")
    HEADERS = {
        "Authorization": f"Bearer {getattr(settings, 'KORAPAY_PUBLIC_KEY', '')}",
        "Content-Type": "application/json",
    }
    BANK_LIST_CACHE_KEY = "korapay_bank_list"
    BANK_LIST_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

    @classmethod
    def get_bank_list(cls):
        logger.info(f"[BANKS][KORAPAY] Fetching bank list...")
        cached_banks = cache.get(cls.BANK_LIST_CACHE_KEY)
        if cached_banks:
            logger.info(f"[BANKS][KORAPAY] Using cached banks count={len(cached_banks)}")
            return cached_banks

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

        url = f"{cls.BASE_URL.rstrip('/')}/misc/banks"
        params = {"countryCode": "NG"}
        try:
            resp = requests.get(url, headers=cls.HEADERS, params=params, timeout=15)
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if not resp.ok or not data.get("status"):
                logger.error(f"[BANKS][KORAPAY][ERR] status={resp.status_code} body={data}")
                raise RuntimeError("Korapay bank list error")

            banks_raw = data.get("data") or []
            banks = [{"name": b.get("name"), "code": b.get("code")} for b in banks_raw if b.get("name") and b.get("code")]
            cache.set(cls.BANK_LIST_CACHE_KEY, banks, cls.BANK_LIST_CACHE_TIMEOUT)
            logger.info(f"[BANKS][KORAPAY][OK] fetched={len(banks)}")
            return banks
        except Exception as e:
            logger.error(f"[BANKS][KORAPAY][EXC] {e}", exc_info=True)
            return fallback_banks

    @classmethod
    def verify_account(cls, account_number, bank_code):
        logger.info(f"[VERIFY][KORAPAY] acct={account_number} bank={bank_code}")
        url = f"{cls.BASE_URL.rstrip('/')}/misc/banks/resolve/"
        payload = {"bank": str(bank_code), "account": str(account_number)}

        try:
            resp = requests.post(url, headers=cls.HEADERS, json=payload, timeout=20)
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if not resp.ok or not data.get("status"):
                logger.error(f"[VERIFY][KORAPAY][ERR] status={resp.status_code} body={data}")
                return None

            d = data.get("data") or {}
            if d.get("account_name"):
                result = {
                    "account_name": d.get("account_name"),
                    "first_name": "",
                    "last_name": "",
                    "other_name": "",
                    "account_number": d.get("account_number"),
                    "bank_code": d.get("bank_code") or bank_code,
                    "bank_name": d.get("bank_name"),
                }
                logger.info(f"[VERIFY][KORAPAY][OK] acct={result['account_number']} bank={result['bank_code']}")
                return result

            logger.warning(f"[VERIFY][KORAPAY] No account_name in response: {data}")
            return None
        except Exception as e:
            logger.error(f"[VERIFY][KORAPAY][EXC] {e}", exc_info=True)
            return None

class FlutterwaveAuthError(Exception):
    pass

class FlutterwaveAuth:
    CACHE_KEY = "flw_v4_access_token"
    CACHE_EXP_KEY = "flw_v4_access_token_exp"
    LOCK_KEY = "flw_v4_token_lock"
    REFRESH_HEADROOM = 60  # seconds before expiry to proactively refresh

    def __init__(self, client_id: str | None = None, client_secret: str | None = None, token_url: str = None):
        self.client_id = client_id or getattr(settings, "FLW_CLIENT_ID", None)
        self.client_secret = client_secret or getattr(settings, "FLW_CLIENT_SECRET", None)
        self.token_url = token_url or "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token"
        if not self.client_id or not self.client_secret:
            raise FlutterwaveAuthError("FLW_CLIENT_ID and FLW_CLIENT_SECRET must be configured")

    def _request_token(self) -> tuple[str, int]:
        resp = requests.post(
            self.token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise FlutterwaveAuthError(f"token request failed: {resp.status_code} {resp.text}")
        j = resp.json()
        access = j.get("access_token")
        expires_in = int(j.get("expires_in", 600))
        if not access:
            raise FlutterwaveAuthError(f"no access_token returned: {j}")
        now = int(time.time())
        expires_at = now + expires_in
        cache.set(self.CACHE_KEY, access, expires_in)
        cache.set(self.CACHE_EXP_KEY, expires_at, expires_in)
        return access, expires_at

    def force_refresh(self) -> str:
        cache.delete(self.CACHE_KEY)
        cache.delete(self.CACHE_EXP_KEY)
        access, _ = self._request_token()
        return access

    def get_access_token(self) -> str:
        access = cache.get(self.CACHE_KEY)
        exp = cache.get(self.CACHE_EXP_KEY)
        now = int(time.time())
        if access and exp and (exp - now > self.REFRESH_HEADROOM):
            return access

        got_lock = cache.add(self.LOCK_KEY, "1", timeout=5)
        try:
            if got_lock:
                access = cache.get(self.CACHE_KEY)
                exp = cache.get(self.CACHE_EXP_KEY)
                now = int(time.time())
                if access and exp and (exp - now > self.REFRESH_HEADROOM):
                    return access
                access, _ = self._request_token()
                return access
            else:
                for _ in range(25):
                    time.sleep(0.2)
                    access = cache.get(self.CACHE_KEY)
                    exp = cache.get(self.CACHE_EXP_KEY)
                    now = int(time.time())
                    if access and exp and (exp - now > self.REFRESH_HEADROOM):
                        return access
                access, _ = self._request_token()
                return access
        finally:
            if got_lock:
                try:
                    cache.delete(self.LOCK_KEY)
                except Exception:
                    pass

    def auth_header(self) -> dict:
        token = self.get_access_token()
        return {"Authorization": f"Bearer {token}"}

    def auth_headers(self, extra: dict | None = None) -> dict:
        h = {"Authorization": f"Bearer {self.get_access_token()}", "Content-Type": "application/json"}
        if extra:
            h.update(extra)
        return h

class FlutterwaveBankService:
    """
    Service for Flutterwave v4 bank list and account resolution.
    """

    @classmethod
    def _env_segment(cls) -> str:
        env = getattr(settings, "FLW_ENV", "developersandbox")
        if env == "developersandbox":
            return "developersandbox"
        return "f4bexperience"

    @classmethod
    def _base_url(cls) -> str:
        return f"https://api.flutterwave.cloud/{cls._env_segment()}"

    @classmethod
    def get_bank_list(cls, country: str = "NG"):
        """
        GET {base}/banks
        Returns a dict: { "status": ..., "message": ..., "data": [...] }
        """
        try:
            auth = FlutterwaveAuth()
        except FlutterwaveAuthError as e:
            logger.error(f"[FLUTTERWAVE][BANK_LIST][AUTH] {e}")
            return {"status": "error", "message": str(e), "data": []}

        url = f"{cls._base_url()}/banks"
        headers = auth.auth_headers()
        params = {"country": country} if country else None

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            j = resp.json()
        except Exception as ex:
            logger.error(f"[FLUTTERWAVE][BANK_LIST][EXC] {ex}")
            return {"status": "error", "message": str(ex), "data": []}

        if resp.status_code // 100 != 2:
            logger.error(f"[FLUTTERWAVE][BANK_LIST][FAIL] {j}")
            return {"status": "error", "message": j.get("message", "Failed to fetch banks"), "data": []}
        return j

    @classmethod
    def verify_account(cls, account_number: str, bank_code: str, currency: str = "NGN"):
        if not bank_code or not account_number:
            return {"status": "error", "message": "bank_code and account_number are required", "data": None}

        def do_request(auth):
            url = f"{cls._base_url()}/banks/account-resolve"
            headers = auth.auth_headers()
            payload = {
                "account": {
                    "number": str(account_number),
                    "code": str(bank_code),
                },
                 "currency": currency
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            return resp

        try:
            auth = FlutterwaveAuth()
            resp = do_request(auth)
            if resp.status_code == 401:
                # Token invalid/expired, force refresh and retry once
                logger.warning("[FLUTTERWAVE][RESOLVE] 401 Unauthorized, refreshing token and retrying...")
                auth.force_refresh()
                resp = do_request(auth)
            j = resp.json()
        except Exception as ex:
            logger.error(f"[FLUTTERWAVE][RESOLVE][EXC] {ex}")
            return {"status": "error", "message": str(ex), "data": None}

        if resp.status_code // 100 != 2:
            logger.error(f"[FLUTTERWAVE][RESOLVE][FAIL] {j}")
            return {"status": "error", "message": j.get("message", "Failed to resolve account"), "data": None}
        return j