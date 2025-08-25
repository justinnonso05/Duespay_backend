# myapp/management/commands/create_platform_vba.py
import uuid

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from main.models import PlatformVBA


class Command(BaseCommand):
    help = "Create a permanent Virtual Bank Account for the platform via Korapay"

    def handle(self, *args, **kwargs):
        # Unique reference
        account_ref = f"duespay-platform-{uuid.uuid4().hex[:8]}"

        payload = {
            "account_name": "DuesPay Checkout Test",
            "account_reference": account_ref,
            "permanent": True,
            "bank_code": "000",  # Sandbox bank code
            "customer": {
                "name": "DuesPay Checkout",
                "email": "chinonsoali2005@gmail.com",
            },
            "kyc": {"bvn": "22222222222"},  # Replace with Korapay's test BVN in sandbox
        }

        headers = {
            "Authorization": f"Bearer {settings.KORAPAY_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        url = "https://api.korapay.com/merchant/api/v1/virtual-bank-account"
        self.stdout.write(self.style.NOTICE("Creating virtual bank account..."))
        response = requests.post(url, json=payload, headers=headers)
        resp_data = response.json()

        if resp_data.get("status") and resp_data.get("data"):
            data = resp_data["data"]
            PlatformVBA.objects.create(
                account_name=data["account_name"],
                account_number=data["account_number"],
                bank_name=data["bank_name"],
                bank_code=data["bank_code"],
                account_reference=data["account_reference"],
                unique_id=data.get("unique_id"),
                account_status=data.get("account_status", "active"),
                currency=data.get("currency", "NGN"),
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Virtual Bank Account created: {data['account_number']} ({data['bank_name']})"
                )
            )
        else:
            self.stdout.write(self.style.ERROR(f"Failed to create VBA: {resp_data}"))
