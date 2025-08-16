from rest_framework import serializers
from .models import PaymentItem, ReceiverBankAccount
from .services import VerifyBankService

class PaymentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentItem
        fields = '__all__'
        read_only_fields = ['association', 'session']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class ReceiverBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiverBankAccount
        fields = ['id', 'account_number', 'account_name', 'bank_name', 'bank_code', 'is_verified', 'created_at']
        read_only_fields = ['id', 'is_verified', 'created_at']

    def validate_account_number(self, value):
        # Basic validation for Nigerian account numbers (10 digits)
        if len(value) != 10 or not value.isdigit():
            raise serializers.ValidationError("Account number must be exactly 10 digits")
        return value

    def validate_bank_code(self, value):
        # Validate that bank code exists in the bank list
        banks = VerifyBankService.get_bank_list()
        valid_codes = [bank.get('code') for bank in banks if bank.get('code')]
        
        if value not in valid_codes:
            raise serializers.ValidationError("Invalid bank code")
        return value


class BankAccountVerificationSerializer(serializers.Serializer):
    """
    Serializer for bank account verification requests
    """
    account_number = serializers.CharField(max_length=10, min_length=10)
    bank_code = serializers.CharField(max_length=10)

    def validate_account_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Account number must contain only digits")
        return value

    def validate_bank_code(self, value):
        try:
            # Validate against available banks
            banks = VerifyBankService.get_bank_list()
            if not banks:
                # If we can't get bank list, allow the validation to pass
                # and let the verification step handle it
                return value
                
            valid_codes = [bank.get('code') for bank in banks if bank.get('code')]
            
            if value not in valid_codes:
                raise serializers.ValidationError("Invalid bank code")
            return value
        except Exception as e:
            # Log the error but don't fail validation here
            # Let the verification step handle bank validation
            return value

    def validate(self, data):
        """
        Cross-field validation
        """
        account_number = data.get('account_number')
        bank_code = data.get('bank_code')

        # Check if both fields are provided
        if not account_number or not bank_code:
            raise serializers.ValidationError("Both account number and bank code are required")
            
        return data


class BankListSerializer(serializers.Serializer):
    """
    Serializer for bank list from Nubapi
    """
    name = serializers.CharField()
    code = serializers.CharField()
    short_name = serializers.CharField(required=False)

    class Meta:
        fields = ['name', 'code', 'short_name']


class BankVerificationResponseSerializer(serializers.Serializer):
    """
    Serializer for successful bank verification response
    """
    status = serializers.CharField(default="success")
    message = serializers.CharField()
    data = serializers.DictField(child=serializers.CharField())

    class Meta:
        fields = ['status', 'message', 'data']

