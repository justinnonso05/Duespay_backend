from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AdminUser
from .models import Association

@receiver(post_save, sender=AdminUser)
def create_association_for_user(sender, instance, created, **kwargs):
    if created:
        Association.objects.create(admin=instance)