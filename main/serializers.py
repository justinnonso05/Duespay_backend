from rest_framework import serializers
from .models import PaySpace, PaymentItem
from django.contrib.auth.models import User

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )
        return user

class PaySpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaySpace
        exclude = ['admin']

class PaymentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentItem
        exclude = ['pay_space']