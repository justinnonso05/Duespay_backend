import requests
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class NubapiService:
    BASE_URL = "https://nubapi.com"
    HEADERS = {
        "Authorization": f"Bearer {getattr(settings, 'NUBAPI_TOKEN', '')}",  
        "Content-Type": "application/json"
    }
    BANK_LIST_CACHE_KEY = "nubapi_bank_list"
    BANK_LIST_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours
    
    @staticmethod
    def get_bank_list():
        """Fetch list of Nigerian banks and their codes from Nubapi."""
        print("Getting bank list...")  # Debug print
        
        cached_banks = cache.get(NubapiService.BANK_LIST_CACHE_KEY)
        if cached_banks:
            print(f"Found cached banks: {len(cached_banks)}")
            return cached_banks

        # Fallback bank list
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
            {"name": "Test Bank", "code": "100004"},  # Added your test bank
        ]

        api_url = f"{NubapiService.BASE_URL}/bank-json"
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            banks = response.json()
            cache.set(NubapiService.BANK_LIST_CACHE_KEY, banks, NubapiService.BANK_LIST_CACHE_TIMEOUT)
            print(f"Fetched {len(banks)} banks from API")
            return banks
        except Exception as e:
            logger.error(f"Error fetching bank list: {e}")
            print(f"Using fallback banks: {len(fallback_banks)}")
            return fallback_banks

    @staticmethod
    def verify_account(account_number, bank_code):
        """Verify bank account details using Nubapi."""
        print(f"Verifying account: {account_number} with bank: {bank_code}")
        
        api_url = f"{NubapiService.BASE_URL}/api/verify"
        params = {
            'account_number': account_number,
            'bank_code': bank_code,
        }
    
        try:
            response = requests.get(api_url, headers=NubapiService.HEADERS, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("account_name"):
                return {
                    "account_name": data.get("account_name"),
                    "first_name": data.get("first_name"),
                    "last_name": data.get("last_name"), 
                    "other_name": data.get("other_name"),
                    "account_number": data.get("account_number"),
                    "bank_code": data.get("bank_code"),
                    "bank_name": data.get("Bank_name"),
                }
            return None
        except Exception as e:
            logger.error(f"Error verifying account: {e}")
            return None

