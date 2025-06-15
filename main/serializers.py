from rest_framework import serializers
from .models import Association, Payer, PaymentItem, Transaction, ReceiverBankAccount
from .models import AdminUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
        read_only_fields = ['is_first_login']

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

    def create(self, validated_data):
        user = AdminUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )
        return user

class PaymentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentItem
        exclude = ['association']

# class TransactionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Transaction
#         fields = '__all__'

class ReceiverBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiverBankAccount
        fields = ['id','bank_name', 'account_name', 'account_number']
        read_only_fields = ['association']

class AssociationSerializer(serializers.ModelSerializer):
    bank_account = ReceiverBankAccountSerializer(read_only=True)
    payment_items = PaymentItemSerializer(many=True, read_only=True)
    # payers = PayerSerializer(many=True, read_only=True)

    class Meta:
        model = Association
        fields = "__all__"
        read_only_fields = ['admin', 'bank_account', 'payment_items']

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

class ProofAndTransactionSerializer(serializers.Serializer):
    association_short_name = serializers.CharField()
    payer = serializers.JSONField()
    payment_item_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    proof_file = serializers.FileField()    