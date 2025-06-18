from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Association
from .serializers import AssociationSerializer

class AssociationViewSet(viewsets.ModelViewSet):
    queryset = Association.objects.all()
    serializer_class = AssociationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        association = getattr(self.request.user, 'association', None)
        if association:
            return Association.objects.filter(pk=association.pk)
        return Association.objects.none()

    def perform_create(self, serializer):
        serializer.save(admin=self.request.user)


class RetrieveAssociationViewSet(generics.RetrieveAPIView):
    queryset = Association.objects.all()
    serializer_class = AssociationSerializer
    lookup_field = 'association_short_name'
    permission_classes = [AllowAny]