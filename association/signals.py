from django.db.models.signals import post_save
from django.dispatch import receiver

from main.models import AdminUser
from transactions.models import Transaction

from .models import Association


@receiver(post_save, sender=AdminUser)
def create_association_for_user(sender, instance, created, **kwargs):
    if created:
        base_short_name = instance.email.split("@")[0].lower()
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
def create_notification_for_transaction(sender, instance, created, **kwargs):
    if created:
        association = instance.association
        payer = f"{instance.payer.first_name} {instance.payer.last_name}"
        message = f"New transaction of ₦{instance.amount_paid} from {payer}."
        association.notifications.create(message=message)
