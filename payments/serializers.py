from rest_framework import serializers

from .bankServices import VerifyBankService
from .models import PaymentItem, ReceiverBankAccount


class PaymentItemSerializer(serializers.ModelSerializer):
    compulsory_for = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[
                ("100", "100 Level"),
                ("200", "200 Level"),
                ("300", "300 Level"),
                ("400", "400 Level"),
                ("500", "500 Level"),
                ("600", "600 Level"),
                ("All Levels", "All Levels"),
            ]
        ),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = PaymentItem
        fields = "__all__"
        read_only_fields = ["association", "session"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value

    def validate_compulsory_for(self, value):
        # Get the current status from the request data
        status = self.initial_data.get('status')
        
        # If status is changing to optional, clear compulsory_for
        if status == "optional":
            return []
        
        # If no levels specified, default to all levels for compulsory items
        if not value and status == "compulsory":
            return ["All Levels"]
        
        # If empty list provided, keep it empty
        if not value:
            return []

        valid_levels = ["100", "200", "300", "400", "500", "600", "All Levels"]
        all_numeric_levels = ["100", "200", "300", "400", "500", "600"]

        # If "All Levels" is explicitly selected, return it
        if "All Levels" in value:
            return ["All Levels"]
        
        # If all numeric levels (100-600) are selected, convert to "All Levels"
        if set(value) == set(all_numeric_levels):
            return ["All Levels"]

        # Validate each level
        for level in value:
            if level not in valid_levels:
                raise serializers.ValidationError(f"Invalid level: {level}")

        return value

    def update(self, instance, validated_data):
        # Handle the business logic for status changes
        new_status = validated_data.get('status', instance.status)
        
        # If changing from compulsory to optional, clear compulsory_for
        if instance.status == "compulsory" and new_status == "optional":
            validated_data['compulsory_for'] = []
        
        return super().update(instance, validated_data)


class ReceiverBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiverBankAccount
        fields = [
            "id",
            "account_number",
            "account_name",
            "bank_name",
            "bank_code",
            "is_verified",
            "created_at",
        ]
        read_only_fields = ["id", "is_verified", "created_at"]

    def validate_account_number(self, value):
        # Basic validation for Nigerian account numbers (10 digits)
        if len(value) != 10 or not value.isdigit():
            raise serializers.ValidationError(
                "Account number must be exactly 10 digits"
            )
        return value

    def validate_bank_code(self, value):
        # Validate that bank code exists in the bank list
        banks = VerifyBankService.get_bank_list()
        valid_codes = [bank.get("code") for bank in banks if bank.get("code")]

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

            valid_codes = [bank.get("code") for bank in banks if bank.get("code")]

            if value not in valid_codes:
                raise serializers.ValidationError("Invalid bank code")
            return value
        except Exception:
            # Log the error but don't fail validation here
            # Let the verification step handle bank validation
            return value

    def validate(self, data):
        """
        Cross-field validation
        """
        account_number = data.get("account_number")
        bank_code = data.get("bank_code")

        # Check if both fields are provided
        if not account_number or not bank_code:
            raise serializers.ValidationError(
                "Both account number and bank code are required"
            )

        return data


class BankListSerializer(serializers.Serializer):
    """
    Serializer for bank list from Nubapi
    """

    name = serializers.CharField()
    code = serializers.CharField()
    short_name = serializers.CharField(required=False)

    class Meta:
        fields = ["name", "code", "short_name"]


class BankVerificationResponseSerializer(serializers.Serializer):
    """
    Serializer for successful bank verification response
    """

    status = serializers.CharField(default="success")
    message = serializers.CharField()
    data = serializers.DictField(child=serializers.CharField())

    class Meta:
        fields = ["status", "message", "data"]
