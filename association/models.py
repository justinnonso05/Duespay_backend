from django.db import models
from main.models import AdminUser
from utils.utils import validate_file_type
from cloudinary.models import CloudinaryField
from datetime import datetime

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
    theme_color = models.CharField(max_length=7, default="#9810fa")
    logo = CloudinaryField('image', folder="Duespay/logos", default="DuesPay/default.jpg", validators=[validate_file_type])
    current_session = models.ForeignKey('Session', null=True, blank=True, on_delete=models.SET_NULL, related_name='current_for_association')

    def __str__(self):
        return f"{self.association_short_name} ({self.Association_type})"
    
    @property
    def logo_url(self):
        return self.logo.url if self.logo else ''

class Session(models.Model):
    association = models.ForeignKey('Association', on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('association', 'title')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.association.association_short_name} - {self.title}"

    def save(self, *args, **kwargs):
        # If this session is being set as active, deactivate other sessions for this association
        if self.is_active:
            Session.objects.filter(association=self.association, is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def generate_default_title(cls):
        current_year = datetime.now().year
        return f"{current_year-1}/{current_year}"

class Notification(models.Model):
    association = models.ForeignKey(Association, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.association.association_short_name}: {self.message[:20]}"