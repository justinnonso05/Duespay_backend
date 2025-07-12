from rest_framework import viewsets, generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Association, Notification
from .serializers import AssociationSerializer, NotificationSerializer
from rest_framework.exceptions import ValidationError

class NotificationPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 10

class AssociationViewSet(viewsets.ModelViewSet):
    queryset = Association.objects.all()
    serializer_class = AssociationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # The authenticated user should be an AdminUser
        try:
            # Since Association has OneToOneField to AdminUser with related_name='association'
            # We can access it directly if the user IS an AdminUser
            if hasattr(self.request.user, 'association'):
                return Association.objects.filter(pk=self.request.user.association.pk)
            return Association.objects.none()
        except (AttributeError, Association.DoesNotExist):
            return Association.objects.none()


class RetrieveAssociationViewSet(generics.RetrieveAPIView):
    queryset = Association.objects.all()
    serializer_class = AssociationSerializer
    lookup_field = 'association_short_name'
    permission_classes = [AllowAny]


class NotificationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all()
    pagination_class = NotificationPagination  # Custom pagination

    def get_queryset(self):
        """
        Get notifications for the authenticated AdminUser's association
        """
        try:
            # Since the user should be an AdminUser with a related Association
            if hasattr(self.request.user, 'association'):
                return Notification.objects.filter(
                    association=self.request.user.association
                ).order_by('-created_at')
            return Notification.objects.none()
        except (AttributeError, Association.DoesNotExist):
            return Notification.objects.none()
    
    def perform_create(self, serializer):
        """
        Automatically set the association when creating a notification
        """
        try:
            if hasattr(self.request.user, 'association'):
                serializer.save(association=self.request.user.association)
            else:
                raise ValidationError("User has no associated association")
        except (AttributeError, Association.DoesNotExist):
            raise ValidationError("Unable to determine user's association")
    
    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """
        Mark all notifications as read for the authenticated user's association
        """
        try:
            if hasattr(request.user, 'association'):
                association = request.user.association
                
                # Get count of unread notifications before updating
                unread_count = Notification.objects.filter(
                    association=association,
                    is_read=False
                ).count()
                
                # Mark all as read
                updated_count = Notification.objects.filter(
                    association=association,
                    is_read=False
                ).update(is_read=True)
                
                return Response({
                    'success': True,
                    'message': f'Marked {updated_count} notifications as read',
                    'updated_count': updated_count,
                    'total_unread_before': unread_count
                }, status=status.HTTP_200_OK)
            
            else:
                return Response({
                    'success': False,
                    'message': 'User has no associated association'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except (AttributeError, Association.DoesNotExist):
            return Response({
                'success': False,
                'message': 'Unable to determine user\'s association'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error marking notifications as read: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """
        Get count of unread notifications for the authenticated user's association
        """
        try:
            if hasattr(request.user, 'association'):
                association = request.user.association
                
                unread_count = Notification.objects.filter(
                    association=association,
                    is_read=False
                ).count()
                
                return Response({
                    'unread_count': unread_count
                }, status=status.HTTP_200_OK)
            
            else:
                return Response({
                    'unread_count': 0
                }, status=status.HTTP_200_OK)
                
        except (AttributeError, Association.DoesNotExist):
            return Response({
                'unread_count': 0
            }, status=status.HTTP_200_OK)
