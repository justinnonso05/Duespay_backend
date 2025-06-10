from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AdminUser, Association, ReceiverBankAccount

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

# @receiver(post_save, sender=Association)
# def create_bank_account_for_association(sender, instance, created, **kwargs):
#     if created:
#         ReceiverBankAccount.objects.create(
#             association=instance,
#             bank_name="--",
#             account_name="--",
#             account_number="--"
#         )