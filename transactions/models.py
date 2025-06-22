from django.db import models
from payers.models import Payer
from association.models import Association
from payments.models import PaymentItem
from .utils import generate_unique_reference_id
import uuid
from utils.utils import validate_file_type
from cloudinary.models import CloudinaryField

class Transaction(models.Model):
    payer = models.ForeignKey(Payer, on_delete=models.CASCADE, related_name='transactions')
    association = models.ForeignKey(Association, on_delete=models.CASCADE, related_name='transactions')
    payment_items = models.ManyToManyField(PaymentItem)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    reference_id = models.CharField(default=generate_unique_reference_id, unique=True, editable=False, max_length=20)
    proof_of_payment = CloudinaryField('file', folder="Duespay/proofs", validators=[validate_file_type])
    is_verified = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.reference_id:
            while True:
                ref = generate_unique_reference_id()
                if not Transaction.objects.filter(reference_id=ref).exists():
                    self.reference_id = ref
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transaction {self.reference_id} by {self.payer}"
    
    @property
    def proof_of_payment_url(self):
        return self.proof_of_payment.url if self.proof_of_payment else ''


# Transaction Receipt model
class TransactionReceipt(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='receipt')
    pdf_file = CloudinaryField('file', folder="DuesPay/transactionReceipts", validators=[validate_file_type])
    receipt_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt {self.receipt_id} for {self.transaction}"
    
    @property
    def pdf_file_url(self):
        return self.pdf_file.url if self.pdf_file else ''
