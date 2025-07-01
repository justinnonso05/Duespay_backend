from rest_framework import serializers
from payments.serializers import PaymentItemSerializer, ReceiverBankAccountSerializer
from .models import Association

class AssociationSerializer(serializers.ModelSerializer):
    bank_account = ReceiverBankAccountSerializer(read_only=True)
    payment_items = PaymentItemSerializer(many=True, read_only=True)
    logo_url = serializers.ReadOnlyField()
    # payers = PayerSerializer(many=True, read_only=True)

    def validate_association_short_name(self, value):
        return value.lower()

    class Meta:
        model = Association
        fields = "__all__"
        read_only_fields = ['admin', 'bank_account', 'payment_items', "logo_url"]
