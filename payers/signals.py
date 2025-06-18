from django.db.models.signals import pre_save
from .emails import send_payer_transaction_verified_email
from django.dispatch import receiver
from transactions.models import Transaction

@receiver(pre_save, sender=Transaction)
def send_verification_email_to_payer(sender, instance, **kwargs):
    if not instance.pk:
        # New transaction, not an update
        return
    try:
        old_instance = Transaction.objects.get(pk=instance.pk)
    except Transaction.DoesNotExist:
        return
    # Check if is_verified changed from False to True
    if not old_instance.is_verified and instance.is_verified:
        send_payer_transaction_verified_email(instance.payer, instance)