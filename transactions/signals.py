from .emails import send_admin_new_transaction_email, send_receipt_email
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transaction, TransactionReceipt

@receiver(post_save, sender=Transaction)
def notify_admin_on_transaction(sender, instance, created, **kwargs):
    if created:
        association = instance.association
        admin = association.admin
        if admin.email:
            send_admin_new_transaction_email(admin, association, instance)

@receiver(post_save, sender=Transaction)
def create_receipt_on_verification(sender, instance, created, **kwargs):
    """Signal: Create and send receipt when transaction is verified"""
    # Only proceed if transaction is verified
    if instance.is_verified:
        try:
            # Get existing receipt or create new one
            receipt, receipt_created = TransactionReceipt.objects.get_or_create(
                transaction=instance
            )
            
            # Always generate and send receipt (whether new or existing)
            send_receipt_email(receipt)
            
            if receipt_created:
                print(f"✅ New receipt created and sent for transaction {instance.reference_id}")
            else:
                print(f"✅ Existing receipt resent for transaction {instance.reference_id}")
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to process receipt for transaction {instance.reference_id}: {str(e)}")