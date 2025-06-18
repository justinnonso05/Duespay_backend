from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ReceiverBankAccount, PaymentItem

@admin.register(ReceiverBankAccount)
class ReceiverBankAccountAdmin(ModelAdmin):
    list_display = ("association", "bank_name", "account_name", "account_number")
    search_fields = ("bank_name", "account_name", "account_number", "association__association_name")
    list_filter = ("bank_name",)

@admin.register(PaymentItem)
class PaymentItemAdmin(ModelAdmin):
    list_display = ("title", "association", "amount", "status", "is_active", "created_at")
    search_fields = ("title", "association__association_name", "status")
    list_filter = ("status", "is_active", "association")
