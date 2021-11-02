"""
Current Home related views.
"""
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.v1_0_0 import serializers
from application.models.models import CurrentHomeImage
from utils import aws


class CurrentHomeImageViewSet(mixins.CreateModelMixin,
                              mixins.UpdateModelMixin,
                              mixins.DestroyModelMixin,
                              viewsets.GenericViewSet):
    """
    Model viewset for model CurrentHomeImage.
    """

    queryset = CurrentHomeImage.objects.all()
    serializer_class = serializers.CurrentHomeImageSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def update(self, request, key=None):
        """
        Custom Update method.
        """
        if key:
            try:
                current_home_image = CurrentHomeImage.objects.get(url=key)
                ser = serializers.CurrentHomeImageSerializer(
                    instance=current_home_image, data=request.data, partial=True)
                ser.is_valid(raise_exception=True)
                if not aws.check_if_object_exists(key):
                    return Response({'url': 'No object found on S3.'}, status=status.HTTP_400_BAD_REQUEST)
                ser.save()
                return Response(ser.data, status=status.HTTP_200_OK)
            except CurrentHomeImage.DoesNotExist:
                return Response({'url': ['Url does not exists.']}, status=status.HTTP_400_BAD_REQUEST)
        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, key=None):
        """
        Custom destroy method to delete file from S3.
        """
        current_home_image = CurrentHomeImage.objects.get(url=key)
        if aws.delete_object(current_home_image.url):
            # Eventually we may want to explore setting the photo
            # task status when enough pictures are deleted.
            current_home_image.delete()
            return Response({}, status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'Couldn\'t delete file from S3.'}, status=status.HTTP_400_BAD_REQUEST)
