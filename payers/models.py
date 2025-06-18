from django.db import models
from association.models import Association

class Payer(models.Model):
    association = models.ForeignKey(Association, on_delete=models.CASCADE, related_name='payers')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    matric_number = models.CharField(max_length=50)
    faculty = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['association', 'email'], name='unique_email_per_association'),
            models.UniqueConstraint(fields=['association', 'phone_number'], name='unique_phone_per_association'),
            models.UniqueConstraint(fields=['association', 'matric_number'], name='unique_matric_per_association'),
        ]