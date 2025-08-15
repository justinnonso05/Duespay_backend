from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import AdminUser, PlatformVBA

@admin.register(AdminUser)
class AdminUserAdmin(ModelAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = ("is_staff", "is_superuser", "is_active")


@admin.register(PlatformVBA)
class PlatformVbaAdmin(ModelAdmin):
    list_display = ("account_name", "account_number", "bank_name", "bank_code", "account_reference", "unique_id", "account_status", "currency")
    search_fields = ("account_name", "account_number", "bank_name", "account_reference", "unique_id")
    list_filter = ("account_status", "currency")
