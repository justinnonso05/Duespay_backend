from django.db import models

from association.models import Association, Session


class Payer(models.Model):
    LEVEL_CHOICES = [
        ("100", "100 Level"),
        ("200", "200 Level"),
        ("300", "300 Level"),
        ("400", "400 Level"),
        ("500", "500 Level"),
        ("600", "600 Level"),
        ("All Levels", "All Levels"),
    ]
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="payers"
    )
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="payers"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="100")
    phone_number = models.CharField(max_length=20)
    matric_number = models.CharField(max_length=50)
    faculty = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "email"], name="unique_email_per_session"
            ),
            models.UniqueConstraint(
                fields=["session", "phone_number"], name="unique_phone_per_session"
            ),
            models.UniqueConstraint(
                fields=["session", "matric_number"], name="unique_matric_per_session"
            ),
        ]
