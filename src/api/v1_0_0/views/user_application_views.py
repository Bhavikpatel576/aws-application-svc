from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from api.v1_0_0 import serializers
from application.models.application import Application


class UserApplicationViewSet(GenericViewSet):
    http_method_names = ['get']
    serializer_class = serializers.UserApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(customer__email=self.request.user.email)

    @action(methods=['get'], detail=False, url_path='active', permission_classes=[IsAuthenticated])
    def get_active_application(self, request):
        #  once we support multiple applications, we can do filtering here to return only whatever definition of active
        #  we decide on
        application = get_object_or_404(self.get_queryset())
        serializer = self.get_serializer(application)
        return Response(serializer.data)
