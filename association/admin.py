from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Association

@admin.register(Association)
class AssociationAdmin(ModelAdmin):
    list_display = ("association_name", "association_short_name", "Association_type", "admin")
    search_fields = ("association_name", "association_short_name", "admin__username")
    list_filter = ("Association_type",)
