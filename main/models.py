from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
import random
import string

def generate_unique_reference_id():
    digits4 = ''.join(random.choices(string.digits, k=4))
    digits3 = ''.join(random.choices(string.digits, k=3))
    letters2 = ''.join(random.choices(string.ascii_uppercase, k=2))
    return f"TX-{digits4}-{digits3}-{letters2}"

class AdminUser(AbstractUser):
    is_first_login = models.BooleanField(default=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

# Association model
class Association(models.Model):
    ASS_CHOICES = [
        ('hall', 'Hall'),
        ('department', 'Department'),
        ('faculty', 'Faculty'),
        ('other', 'Other'),
    ]

    admin = models.OneToOneField(AdminUser, on_delete=models.CASCADE, related_name='association')
    association_name = models.CharField(max_length=255, unique=True, default="other")
    association_short_name = models.CharField(max_length=50, unique=True, default="other")
    Association_type = models.CharField(max_length=20, choices=ASS_CHOICES, default="Other")
    logo = models.ImageField(upload_to='logos/', default="logos/sharingan.png")

    def __str__(self):
        return f"{self.association_short_name} ({self.Association_type})"


# Receiver Bank Account model
class ReceiverBankAccount(models.Model):
    association = models.OneToOneField(Association, on_delete=models.CASCADE, related_name='bank_account')
    bank_name = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.account_name} - {self.bank_name}"


# Payment Item model
class PaymentItem(models.Model):
    STATUS_CHOICES = [
        ('compulsory', 'Compulsory'),
        ('optional', 'Optional'),
    ]

    association = models.ForeignKey(Association, on_delete=models.CASCADE, related_name='payment_items')
    title = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.status}"


# Payer model
class Payer(models.Model):
    association = models.ForeignKey(Association, on_delete=models.CASCADE, related_name='payers')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    matric_number = models.CharField(max_length=50)
    faculty = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['association', 'email'], name='unique_email_per_association'),
            models.UniqueConstraint(fields=['association', 'phone_number'], name='unique_phone_per_association'),
            models.UniqueConstraint(fields=['association', 'matric_number'], name='unique_matric_per_association'),
        ]

# Transaction model
class Transaction(models.Model):
    payer = models.ForeignKey(Payer, on_delete=models.CASCADE, related_name='transactions')
    association = models.ForeignKey(Association, on_delete=models.CASCADE, related_name='transactions')
    payment_items = models.ManyToManyField(PaymentItem)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    reference_id = models.CharField(default=generate_unique_reference_id, unique=True, editable=False, max_length=20)
    proof_of_payment = models.FileField(upload_to='DuesPay/proofs/')
    is_verified = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.reference_id:
            while True:
                ref = self.generate_unique_reference_id()
                if not Transaction.objects.filter(reference_id=ref).exists():
                    self.reference_id = ref
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transaction {self.reference_id} by {self.payer}"


# Transaction Receipt model
class TransactionReceipt(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='receipt')
    pdf_file = models.FileField(upload_to='DuesPay/receipts/')
    receipt_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt {self.receipt_id} for {self.transaction}"
