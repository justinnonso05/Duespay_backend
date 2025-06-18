from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import AdminUser

@admin.register(AdminUser)
class AdminUserAdmin(ModelAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = ("is_staff", "is_superuser", "is_active")
