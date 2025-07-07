from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Transaction, TransactionReceipt

@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ("reference_id", "payer", "association", "amount_paid", "is_verified", "submitted_at")
    search_fields = ("reference_id", "payer__matric_number", "payer__email", "association__association_name")
    list_filter = ("is_verified", "association", "submitted_at")

@admin.register(TransactionReceipt)
class TransactionReceiptAdmin(ModelAdmin):
    list_display = ("receipt_no", "transaction", "issued_at")
    search_fields = ("receipt_no", "transaction__reference_id")
    list_filter = ("issued_at",)
