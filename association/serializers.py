from datetime import date
import re

from rest_framework import serializers

from payments.serializers import PaymentItemSerializer, ReceiverBankAccountSerializer

from .models import Association, Notification, Session


class AssociationSerializer(serializers.ModelSerializer):
    bank_account = ReceiverBankAccountSerializer(read_only=True)
    payment_items = serializers.SerializerMethodField()
    logo_url = serializers.ReadOnlyField()
    # payers = PayerSerializer(many=True, read_only=True)

    def get_payment_items(self, obj):
        """Return payment items for the current session only"""
        if obj.current_session:
            from payments.models import PaymentItem

            payment_items = PaymentItem.objects.filter(
                association=obj, session=obj.current_session
            )
            return PaymentItemSerializer(payment_items, many=True).data
        return []

    def validate_association_short_name(self, value):
        value = value.lower()
        
        if not re.match(r'^[a-z0-9-]+$', value):
            raise serializers.ValidationError(
                "Short name can only contain lowercase letters, numbers, and hyphens."
            )
  
        if value.startswith('-') or value.endswith('-'):
            raise serializers.ValidationError(
                "Short name cannot start or end with a hyphen."
            )

        if '--' in value:
            raise serializers.ValidationError(
                "Short name cannot contain consecutive hyphens."
            )

        if not value.strip():
            raise serializers.ValidationError(
                "Short name cannot be empty."
            )
        return value

    def create(self, validated_data):
        """Set the admin to the current user when creating"""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["admin"] = request.user
        # Check if the user already has an association
        if hasattr(request.user, "association") and request.user.association is not None:
            raise serializers.ValidationError({"association": "Association already exists for this user."})
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Don't allow changing the admin during updates"""
        validated_data.pop("admin", None)
        return super().update(instance, validated_data)

    class Meta:
        model = Association
        fields = "__all__"
        read_only_fields = ["admin", "bank_account", "payment_items", "logo_url"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ["id", "title", "start_date", "end_date", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_title(self, value):
        # Get association from context (for create) or from instance (for update)
        association = self.context.get("association")
        if not association and self.instance:
            association = self.instance.association

        if association:
            # Exclude current instance during update to allow keeping same title
            existing_sessions = Session.objects.filter(association=association, title=value)
            if self.instance:
                existing_sessions = existing_sessions.exclude(pk=self.instance.pk)
            
            if existing_sessions.exists():
                raise serializers.ValidationError(
                    "A session with this title already exists for this association."
                )
        return value

    def create(self, validated_data):
        # Get association from context
        association = self.context.get("association")
        validated_data["association"] = association
        if not validated_data.get("start_date"):
            validated_data["start_date"] = date.today()
        return super().create(validated_data)


class AssociationProfileSerializer(serializers.ModelSerializer):
    current_session = SessionSerializer(read_only=True)
    logo_url = serializers.ReadOnlyField()

    class Meta:
        model = Association
        fields = [
            "id",
            "association_name",
            "association_short_name",
            "association_type",
            "theme_color",
            "logo_url",
            "current_session",
        ]


class AdminProfileSerializer(serializers.Serializer):
    admin = serializers.SerializerMethodField()
    association = AssociationProfileSerializer(read_only=True)

    def get_admin(self, obj):
        return {
            "id": obj.admin.id,
            "email": obj.admin.email,
            # 'username': obj.admin.username,
            "first_name": obj.admin.first_name,
            "last_name": obj.admin.last_name,
        }
