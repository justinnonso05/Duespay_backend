from django.db import models
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from association.models import Association, Session

from .models import Payer
from .serializers import PayerCheckSerializer, PayerSerializer
from .services import PayerService


class PayerCheckView(APIView):

    def post(self, request):
        serializer = PayerCheckSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data

        assoc_short_name = data.get("association_short_name")
        try:
            association = Association.objects.get(
                association_short_name=assoc_short_name
            )
        except Association.DoesNotExist:
            return Response(
                {"error": "Association not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if association has a current session
        if not association.current_session:
            return Response(
                {
                    "error": "Association has no active session. Please contact the association admin."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payer, error = PayerService.check_or_update_payer(
            association,
            association.current_session,  # Pass the session instance
            data["matric_number"],
            data["email"],
            data["phone_number"],
            data["first_name"],
            data["last_name"],
            data.get("faculty", ""),
            data.get("department", ""),
        )
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "success": True,
                "payer_id": payer.id,
                "message": "Payer found or updated successfully.",
            },
            status=200,
        )


class PayerViewSet(viewsets.ModelViewSet):
    queryset = Payer.objects.all()
    serializer_class = PayerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        association = getattr(self.request.user, "association", None)
        queryset = Payer.objects.none()

        if association:
            # Get session_id from query params or use current session
            session_id = self.request.query_params.get("session_id")

            if session_id:
                # Validate that session belongs to this association
                try:
                    session = Session.objects.get(
                        id=session_id, association=association
                    )
                    queryset = Payer.objects.filter(session=session)
                except Session.DoesNotExist:
                    queryset = Payer.objects.none()
            elif association.current_session:
                # Use current session if no session_id provided
                queryset = Payer.objects.filter(session=association.current_session)
            else:
                # No session available, return empty queryset
                queryset = Payer.objects.none()

        # Order by creation date
        queryset = queryset.order_by("-created_at")

        # Search by name, matric number, email, faculty, department
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search)
                | models.Q(last_name__icontains=search)
                | models.Q(matric_number__icontains=search)
                | models.Q(email__icontains=search)
                | models.Q(faculty__icontains=search)
                | models.Q(department__icontains=search)
            )

        # Filter by faculty
        faculty = self.request.query_params.get("faculty")
        if faculty:
            queryset = queryset.filter(faculty__iexact=faculty)

        # Filter by department
        department = self.request.query_params.get("department")
        if department:
            queryset = queryset.filter(department__iexact=department)

        return queryset

    def perform_create(self, serializer):
        association = getattr(self.request.user, "association", None)
        if not association or not association.current_session:
            raise ValidationError(
                "No current session available. Please create a session first."
            )

        serializer.save(
            association=association,
            session=association.current_session,  # Auto-assign current session
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)
