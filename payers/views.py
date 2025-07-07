import json
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import models
from rest_framework.permissions import IsAuthenticated, AllowAny
from .services import PayerService
from .serializers import (
    PayerCheckSerializer, PayerSerializer, 
)
from association.models import Association
from .models import Payer

class PayerCheckView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PayerCheckSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data

        assoc_short_name = data.get('association_short_name')
        try:
            association = Association.objects.get(association_short_name=assoc_short_name)
        except Association.DoesNotExist:
            return Response({"error": "Association not found."}, status=status.HTTP_404_NOT_FOUND)

        payer, error = PayerService.check_or_update_payer(
            association,
            data['matric_number'],
            data['email'],
            data['phone_number'],
            data['first_name'],
            data['last_name'],
            data.get('faculty', ''),
            data.get('department', '')
        )
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "success": True,
            "payer_id": payer.id,
            "message": "Payer found or updated successfully."
        }, status=200)
    
class PayerViewSet(viewsets.ModelViewSet):
    queryset = Payer.objects.all()
    serializer_class = PayerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        association = getattr(self.request.user, 'association', None)
        queryset = Payer.objects.none()
        if association:
            queryset = Payer.objects.filter(association=association).order_by('-created_at')

        # Search by name, matric number, email, faculty, department
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(matric_number__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(faculty__icontains=search) |
                models.Q(department__icontains=search)
            )

        # Filter by faculty
        faculty = self.request.query_params.get('faculty')
        if faculty:
            queryset = queryset.filter(faculty__iexact=faculty)

        # Filter by department
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department__iexact=department)

        return queryset

    def perform_create(self, serializer):
        serializer.save(association=self.request.user.association)
        
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)