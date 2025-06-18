from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import PaymentItem, ReceiverBankAccount
from .serializers import PaymentItemSerializer, ReceiverBankAccountSerializer

class PaymentItemViewSet(viewsets.ModelViewSet):
    queryset = PaymentItem.objects.all()
    serializer_class = PaymentItemSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        association = self.request.user.association
        serializer.save(association=association)

    def get_queryset(self):
        association = getattr(self.request.user, 'association', None)
        queryset = PaymentItem.objects.none()
        if association:
            queryset = PaymentItem.objects.filter(association=association)

        # Search by title
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)

        # Filter by is_active (status)
        status = self.request.query_params.get('status')
        if status is not None:
            if status.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif status.lower() == 'false':
                queryset = queryset.filter(is_active=False)

        # Filter by type (status field: 'optional' or 'compulsory')
        type_param = self.request.query_params.get('type')
        if type_param:
            queryset = queryset.filter(status__iexact=type_param)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if not queryset.exists():
            return Response({"results": [], "count": 0, "message": "No payment items found."})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
        

class ReceiverBankAccountViewSet(viewsets.ModelViewSet):
    queryset = ReceiverBankAccount.objects.all()
    serializer_class = ReceiverBankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        association = getattr(self.request.user, 'association', None)
        if association:
            return ReceiverBankAccount.objects.filter(association=association)
        return ReceiverBankAccount.objects.none()

    def perform_create(self, serializer):
        association = self.request.user.association
        serializer.save(association=association)