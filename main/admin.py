from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import AdminUser, Association, ReceiverBankAccount, PaymentItem, Transaction, TransactionReceipt, Payer

@admin.register(AdminUser)
class AdminUserAdmin(ModelAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = ("is_staff", "is_superuser", "is_active")

@admin.register(Association)
class AssociationAdmin(ModelAdmin):
    list_display = ("association_name", "association_short_name", "Association_type", "admin")
    search_fields = ("association_name", "association_short_name", "admin__username")
    list_filter = ("Association_type",)

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

@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ("reference_id", "payer", "association", "amount_paid", "is_verified", "submitted_at")
    search_fields = ("reference_id", "payer__matric_number", "payer__email", "association__association_name")
    list_filter = ("is_verified", "association", "submitted_at")

@admin.register(TransactionReceipt)
class TransactionReceiptAdmin(ModelAdmin):
    list_display = ("receipt_id", "transaction", "issued_at")
    search_fields = ("receipt_id", "transaction__reference_id")
    list_filter = ("issued_at",)

@admin.register(Payer)
class PayerAdmin(ModelAdmin):
    list_display = ("first_name", "last_name", "matric_number", "email", "association", "faculty", "department")
    search_fields = ("first_name", "last_name", "matric_number", "email", "association__association_name")
    list_filter = ("association", "faculty", "department")