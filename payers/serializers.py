from rest_framework import serializers
from .models import Payer

class PayerSerializer(serializers.ModelSerializer):
    total_transactions = serializers.SerializerMethodField()

    class Meta:
        model = Payer
        fields = '__all__'
        read_only_fields = ['association']

    def get_total_transactions(self, obj):
        return obj.transactions.count()

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['association'] = user.association
        return super().create(validated_data)
    
class PayerCheckSerializer(serializers.Serializer):
    association_short_name = serializers.CharField()
    matric_number = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    faculty = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    department = serializers.CharField(required=False, allow_blank=True, allow_null=True)
