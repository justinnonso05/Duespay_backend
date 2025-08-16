from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from decimal import Decimal
import json
import time

from transactions.models import Transaction
from payments.models import ReceiverBankAccount
from main.services import korapay_payout_bank
from django.conf import settings


class Command(BaseCommand):
    help = "Manually trigger a Korapay payout for a transaction."

    def add_arguments(self, parser):
        parser.add_argument("--ref", type=str, help="Transaction reference_id to payout. If omitted, uses latest verified transaction.")
        parser.add_argument("--amount", type=str, help="Override amount to payout (NGN). Defaults to txn.amount_paid.")
        parser.add_argument("--payout-ref", type=str, help="Override payout reference. Defaults to '<txn_ref>-OUT'.")
        parser.add_argument("--unique", action="store_true", help="Append a timestamp to payout reference to avoid duplicate-reference errors.")
        parser.add_argument("--dry-run", action="store_true", help="Print what would be sent without calling Korapay.")

    def handle(self, *args, **options):
        ref = options.get("ref")
        override_amount = options.get("amount")
        custom_payout_ref = options.get("payout_ref")
        make_unique = bool(options.get("unique"))
        dry_run = bool(options.get("dry_run"))

        # Locate transaction
        if ref:
            try:
                txn = Transaction.objects.get(reference_id=ref)
            except Transaction.DoesNotExist:
                raise CommandError(f"No Transaction with reference_id={ref}")
        else:
            txn = Transaction.objects.filter(is_verified=True).order_by("-id").first()
            if not txn:
                raise CommandError("No verified transactions found. Provide --ref or verify a transaction first.")

        # Receiver bank
        rcv = ReceiverBankAccount.objects.filter(association=txn.association).first()
        if not rcv:
            raise CommandError(f"No ReceiverBankAccount for association_id={txn.association_id}")

        # Amount
        if override_amount:
            try:
                amount = Decimal(str(override_amount))
            except Exception:
                raise CommandError(f"Invalid --amount value: {override_amount}")
        else:
            amount = txn.amount_paid

        # Payout reference (idempotent)
        payout_ref = custom_payout_ref or f"{txn.reference_id}-OUT"
        if make_unique:
            payout_ref = f"{payout_ref}-{int(time.time())}"
        payout_ref = payout_ref[:40]  # provider limit safety

        # Customer (association)
        assoc = txn.association
        assoc_name = (
            getattr(assoc, "association_name", None)
            or getattr(assoc, "association_short_name", None)
            or str(assoc)
        )
        assoc_email = (
            getattr(getattr(assoc, "adminuser", None), "email", None)
            or getattr(getattr(assoc, "admin", None), "email", None)
            or getattr(settings, "PLATFORM_EMAIL", "justondev05@gmail.com")
        )

        narration = f"Dues payout {txn.reference_id}"[:80]
        bank_code = getattr(rcv, "bank_code", "") or ""
        account_number = getattr(rcv, "account_number", "") or ""

        # Print summary
        now = timezone.now().isoformat()
        self.stdout.write(self.style.MIGRATE_HEADING("== Payout test =="))
        self.stdout.write(f"time={now}")
        self.stdout.write(f"txn_ref={txn.reference_id} payout_ref={payout_ref}")
        self.stdout.write(f"amount={amount}")
        self.stdout.write(f"bank_code={bank_code} account_number={account_number}")
        self.stdout.write(f"customer_name={assoc_name} customer_email={assoc_email}")
        self.stdout.write(f"KORAPAY_BASE_URL={getattr(settings, 'KORAPAY_BASE_URL', '')}")
        self.stdout.write("")

        if dry_run:
            payload_preview = {
                "reference": payout_ref,
                "destination": {
                    "type": "bank_account",
                    "amount": float(amount) if amount != amount.to_integral() else int(amount),
                    "currency": "NGN",
                    "narration": narration,
                    "bank_account": {"bank": bank_code, "account": account_number},
                    "customer": {"name": assoc_name, "email": assoc_email},
                },
            }
            self.stdout.write(self.style.WARNING("Dry-run. Would send payload:"))
            self.stdout.write(json.dumps(payload_preview, indent=2))
            return

        # Execute payout
        try:
            resp = korapay_payout_bank(
                amount=str(amount),
                bank_code=bank_code,
                account_number=account_number,
                reference=payout_ref,
                narration=narration,
                customer={"name": assoc_name, "email": assoc_email},
            )
            self.stdout.write(self.style.SUCCESS("Payout initiated successfully."))
            self.stdout.write(json.dumps(resp, indent=2))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Payout failed: {e}"))
            self.stderr.write("Common causes: IP not whitelisted, insufficient wallet balance, invalid bank/account, duplicate reference.")
            raise