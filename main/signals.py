from django.db.models.signals import pre_save
from .emails import send_admin_new_transaction_email, send_payer_transaction_verified_email
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AdminUser, Association, ReceiverBankAccount, Transaction

@receiver(post_save, sender=AdminUser)
def create_association_for_user(sender, instance, created, **kwargs):
    if created:
        base_short_name = instance.username.lower()
        short_name = base_short_name
        counter = 1
        while Association.objects.filter(association_short_name=short_name).exists():
            short_name = f"{base_short_name}{counter}"
            counter += 1
        Association.objects.create(
            admin=instance,
            association_name=f"{instance.first_name} {instance.last_name} Association",
            association_short_name=short_name,
        )


@receiver(post_save, sender=Transaction)
def notify_admin_on_transaction(sender, instance, created, **kwargs):
    if created:
        association = instance.association
        admin = association.admin
        if admin.email:
            send_admin_new_transaction_email(admin, association, instance)



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