from rest_framework import serializers
from .models import AdminUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import re

def check_password(value):
    if len(value) < 6:
        raise serializers.ValidationError("Password must be at least 6 characters long.")
    
    if not re.search(r'[A-Z]', value):
        raise serializers.ValidationError("Password must contain at least one uppercase letter.")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
        raise serializers.ValidationError("Password must contain at least one special character.")

class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, required=False)

    class Meta:
        model = AdminUser
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'password']
        read_only_fields = ['is_first_login']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = AdminUser.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        data['is_first_login'] = self.user.is_first_login

        if self.user.is_first_login:
            self.user.is_first_login = False
            self.user.save()

        return data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = AdminUser
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'password']

    def validate_password(self, value):
        check_password(value)
        return value

    def create(self, validated_data):
        user = AdminUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )
        return user

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    uid = serializers.IntegerField()  # Add uid to serializer
    password = serializers.CharField(min_length=6)

    def validate_password(self, value):
        check_password(value)
        return value