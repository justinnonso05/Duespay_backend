from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Payer

@admin.register(Payer)
class PayerAdmin(ModelAdmin):
    list_display = ("first_name", "last_name", "matric_number", "email", "association", "faculty", "department")
    search_fields = ("first_name", "last_name", "matric_number", "email", "association__association_name")
    list_filter = ("association", "faculty", "department")