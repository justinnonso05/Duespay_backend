from django.db import models
from main.models import AdminUser

class Association(models.Model):
    ASS_CHOICES = [
        ('hall', 'Hall'),
        ('department', 'Department'),
        ('faculty', 'Faculty'),
        ('other', 'Other'),
    ]

    admin = models.OneToOneField(AdminUser, on_delete=models.CASCADE, related_name='association')
    association_name = models.CharField(max_length=255, unique=True, default="other")
    association_short_name = models.CharField(max_length=50, unique=True, default="other")
    Association_type = models.CharField(max_length=20, choices=ASS_CHOICES, default="Other")
    logo = models.ImageField(upload_to='logos/', default="logos/sharingan.png")

    def __str__(self):
        return f"{self.association_short_name} ({self.Association_type})"
