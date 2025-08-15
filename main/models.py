from django.db import models
from django.contrib.auth.models import AbstractUser

class AdminUser(AbstractUser):
    is_first_login = models.BooleanField(default=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True, blank=False, null=False)

class PlatformVBA(models.Model):
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20, unique=True)
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=10)
    account_reference = models.CharField(max_length=100, unique=True)
    unique_id = models.CharField(max_length=100, blank=True, null=True) 
    account_status = models.CharField(max_length=50, default='active')
    currency = models.CharField(max_length=10, default='NGN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.account_name} ({self.account_number})"
