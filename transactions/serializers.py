from rest_framework import serializers

from .models import Transaction, TransactionReceipt


class TransactionSerializer(serializers.ModelSerializer):
    payment_item_titles = serializers.SerializerMethodField()
    payer_first_name = serializers.CharField(source="payer.first_name", read_only=True)
    payer_last_name = serializers.CharField(source="payer.last_name", read_only=True)
    payer_matric = serializers.CharField(source="payer.matric_number", read_only=True)
    payer_email = serializers.CharField(source="payer.email", read_only=True)
    payer_name = serializers.SerializerMethodField()
    proof_of_payment_url = serializers.ReadOnlyField()

    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = ["payer_name", "payment_item", "payer_matric", "payer_email", "proof_of_payment_url"]

    def get_payment_item_titles(self, obj):
        return [item.title for item in obj.payment_items.all()]

    def get_payer_name(self, obj):
        return f"{obj.payer.first_name} {obj.payer.last_name}"

    def create(self, validated_data):
        user = self.context["request"].user
        payer = user.payer
        association = payer.association
        validated_data["payer"] = payer
        validated_data["association"] = association

        # Get session from validated data or use current session
        session = validated_data.get("session")
        if not session:
            session = association.current_session
            if not session:
                raise serializers.ValidationError(
                    "No current session available. Please create a session first."
                )
            validated_data["session"] = session

        return super().create(validated_data)


class ProofAndTransactionSerializer(serializers.Serializer):
    association_short_name = serializers.CharField()
    payer = serializers.JSONField()
    payment_item_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    proof_file = serializers.FileField()


class TransactionReceiptDetailSerializer(serializers.ModelSerializer):
    transaction_reference_id = serializers.CharField(source="transaction.reference_id")
    payer_first_name = serializers.CharField(source="transaction.payer.first_name")
    payer_last_name = serializers.CharField(source="transaction.payer.last_name")
    payer_level = serializers.CharField(source="transaction.payer.level")
    amount_paid = serializers.DecimalField(
        source="transaction.amount_paid", max_digits=10, decimal_places=2
    )
    items_paid = serializers.SerializerMethodField()
    issued_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    association_name = serializers.CharField(
        source="transaction.association.association_name"
    )
    association_short_name = serializers.CharField(
        source="transaction.association.association_short_name"
    )
    association_logo = serializers.ImageField(source="transaction.association.logo")
    association_theme_color = serializers.CharField(
        source="transaction.association.theme_color"
    )
    receipt_no = serializers.SerializerMethodField()
    receipt_id = serializers.CharField(read_only=True)
    session_title = serializers.CharField(
        source="transaction.session.title", allow_null=True, default="N/A"
    )

    class Meta:
        model = TransactionReceipt
        fields = [
            "receipt_id",
            "receipt_no",
            "session_title",
            "payer_level",
            "issued_at",
            "transaction_reference_id",
            "payer_first_name",
            "payer_last_name",
            "amount_paid",
            "items_paid",
            "association_name",
            "association_short_name",
            "association_logo",
            "association_theme_color",
        ]

    def get_receipt_no(self, obj):
        association_short = obj.transaction.association.association_short_name.upper()
        receipt_no = obj.receipt_no
        current_year_short = obj.issued_at.strftime("%y")
        return f"{association_short}/{receipt_no}/{current_year_short}"

    def get_items_paid(self, obj):
        return [item.title for item in obj.transaction.payment_items.all()]
