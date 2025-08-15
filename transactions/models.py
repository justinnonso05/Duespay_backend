import uuid
from django.db import models
from payers.models import Payer
from association.models import Association, Session
from payments.models import PaymentItem
from .utils import generate_unique_reference_id
from utils.utils import validate_file_type
from cloudinary.models import CloudinaryField

class Transaction(models.Model):
    payer = models.ForeignKey(Payer, on_delete=models.CASCADE, related_name='transactions')
    association = models.ForeignKey(Association, on_delete=models.CASCADE, related_name='transactions')
    payment_items = models.ManyToManyField(PaymentItem)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    reference_id = models.CharField(default=generate_unique_reference_id, unique=True, editable=False, max_length=20)
    proof_of_payment = CloudinaryField('file', folder="Duespay/proofs", validators=[validate_file_type], blank=True, null=True)  # made optional
    is_verified = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='transactions')
    
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
    receipt_id = models.CharField(default=uuid.uuid4, unique=True, editable=False, max_length=36)
    receipt_no = models.CharField(max_length=10, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Remove the constraint that uses lookup syntax
        pass

    def save(self, *args, **kwargs):
        if not self.receipt_no:
            # Get the association from the related transaction
            association = self.transaction.association
            
            # Get the highest receipt number for this association
            last_receipt = TransactionReceipt.objects.filter(
                transaction__association=association
            ).order_by('-receipt_no').first()
            
            if last_receipt:
                # Extract the numeric part and increment
                last_number = int(last_receipt.receipt_no)
                new_number = last_number + 1
            else:
                # First receipt for this association
                new_number = 1
            
            # Format as 5-digit zero-padded string
            self.receipt_no = f"{new_number:05d}"
        
        super().save(*args, **kwargs)

    def clean(self):
        # Add validation to ensure uniqueness per association
        if self.pk is None:  # Only for new instances
            association = self.transaction.association
            if TransactionReceipt.objects.filter(
                transaction__association=association,
                receipt_no=self.receipt_no
            ).exists():
                from django.core.exceptions import ValidationError
                raise ValidationError("Receipt number already exists for this association")

    def __str__(self):
        return f"Receipt {self.receipt_no} for {self.transaction.reference_id}"
    
    @property
    def pdf_file_url(self):
        return self.pdf_file.url if self.pdf_file else ''
