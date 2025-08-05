from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Association, Notification, Session

@admin.register(Association)
class AssociationAdmin(ModelAdmin):
    list_display = ("association_name", "association_short_name", "Association_type", "admin")
    search_fields = ("association_name", "association_short_name", "admin__username")
    list_filter = ("Association_type",)

@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("message", "is_read", "association__association_short_name")

@admin.register(Session)
class SessionAdmin(ModelAdmin):
    list_display = ("title", "association", "start_date", "end_date", "is_active")
    search_fields = ("title", "association__association_short_name")
    list_filter = ("is_active", "association")
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('association')