from django.db import models
from association.models import Association, Session
import datetime

class Payer(models.Model):
    association = models.ForeignKey(Association, on_delete=models.CASCADE, related_name='payers')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='payers')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    matric_number = models.CharField(max_length=50)
    faculty = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['session', 'email'], name='unique_email_per_session'),
            models.UniqueConstraint(fields=['session', 'phone_number'], name='unique_phone_per_session'),
            models.UniqueConstraint(fields=['session', 'matric_number'], name='unique_matric_per_session'),
        ]