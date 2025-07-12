from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Association, Notification

@admin.register(Association)
class AssociationAdmin(ModelAdmin):
    list_display = ("association_name", "association_short_name", "Association_type", "admin")
    search_fields = ("association_name", "association_short_name", "admin__username")
    list_filter = ("Association_type",)

@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("message", "is_read", "association__association_short_name")