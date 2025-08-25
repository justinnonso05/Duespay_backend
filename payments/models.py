from django.db import models

from association.models import Association, Session


class ReceiverBankAccount(models.Model):
    association = models.OneToOneField(
        Association, on_delete=models.CASCADE, related_name="bank_account"
    )
    bank_name = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    bank_code = models.CharField(max_length=10, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.account_name} - {self.bank_name}"


class PaymentItem(models.Model):
    STATUS_CHOICES = [
        ("compulsory", "Compulsory"),
        ("optional", "Optional"),
    ]
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="payment_items"
    )
    title = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="payment_items"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.status}"
