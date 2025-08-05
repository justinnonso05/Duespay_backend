from rest_framework import serializers
from .models import PaymentItem, ReceiverBankAccount

class PaymentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentItem
        exclude = ['association']
        
    def create(self, validated_data):
        # Get association from context (set in view)
        association = self.context.get('association')
        
        # Get session from validated data or use current session
        session = validated_data.get('session')
        if not session and association:
            session = association.current_session
            if not session:
                raise serializers.ValidationError("No current session available. Please create a session first.")
            validated_data['session'] = session
            
        validated_data['association'] = association
        return super().create(validated_data)

class ReceiverBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiverBankAccount
        fields = ['id','bank_name', 'account_name', 'account_number']
        read_only_fields = ['association']

