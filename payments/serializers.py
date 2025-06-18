from rest_framework import serializers
from .models import PaymentItem, ReceiverBankAccount

class PaymentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentItem
        exclude = ['association']

class ReceiverBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiverBankAccount
        fields = ['id','bank_name', 'account_name', 'account_number']
        read_only_fields = ['association']

