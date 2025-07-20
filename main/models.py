from django.db import models
from django.contrib.auth.models import AbstractUser

class AdminUser(AbstractUser):
    is_first_login = models.BooleanField(default=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True, blank=False, null=False)