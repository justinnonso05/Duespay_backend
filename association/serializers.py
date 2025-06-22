from rest_framework import serializers
from payments.serializers import PaymentItemSerializer, ReceiverBankAccountSerializer
from .models import Association
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class AssociationSerializer(serializers.ModelSerializer):
    bank_account = ReceiverBankAccountSerializer(read_only=True)
    payment_items = PaymentItemSerializer(many=True, read_only=True)
    logo_url = serializers.ReadOnlyField()
    # payers = PayerSerializer(many=True, read_only=True)

    class Meta:
        model = Association
        fields = "__all__"
        read_only_fields = ['admin', 'bank_account', 'payment_items', "logo_url"]

    # def create(self, validated_data):
    #     validated_data['association_short_name'] = validated_data['association_short_name'].lower()
    #     association = Association.objects.create_association(
    #         association_short_name=validated_data['association_short_name']
    #     )

    #     return association