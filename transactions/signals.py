from .emails import send_admin_new_transaction_email
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transaction

@receiver(post_save, sender=Transaction)
def notify_admin_on_transaction(sender, instance, created, **kwargs):
    if created:
        association = instance.association
        admin = association.admin
        if admin.email:
            send_admin_new_transaction_email(admin, association, instance)
