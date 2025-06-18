from rest_framework import serializers
from .models import Transaction

class TransactionSerializer(serializers.ModelSerializer):
    payment_item_titles = serializers.SerializerMethodField()
    payer_first_name = serializers.CharField(source='payer.first_name', read_only=True)
    payer_last_name = serializers.CharField(source='payer.last_name', read_only=True)
    payer_name = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['payer_name', 'payment_item']

    def get_payment_item_titles(self, obj):
        return [item.title for item in obj.payment_items.all()]

    def get_payer_name(self, obj):
        return f"{obj.payer.first_name} {obj.payer.last_name}"

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['payer'] = user.payer
        return super().create(validated_data)

class ProofAndTransactionSerializer(serializers.Serializer):
    association_short_name = serializers.CharField()
    payer = serializers.JSONField()
    payment_item_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    proof_file = serializers.FileField()  