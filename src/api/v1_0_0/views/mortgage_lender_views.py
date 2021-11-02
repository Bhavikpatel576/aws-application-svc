"""
Lender related views.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.v1_0_0 import serializers
from application.models.application import Application

class MortgageLenderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.application_serializers.MortgageLenderSerializer
    http_method_names = ['put']

    @action(methods=['put'], detail=False, url_path='application-mortgage-lender', permission_classes=[IsAuthenticated])
    def update_mortgage_lender(self, request):
        app_id = request.data.pop('application_id')
        if not app_id:
            return Response("Payload missing application_id", status=status.HTTP_400_BAD_REQUEST)
        application = get_object_or_404(Application, pk=app_id)
        if application.mortgage_lender:
            serializer = self.get_serializer(application.mortgage_lender, data=request.data)
        else:
            serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            mortgage_lender = serializer.save()
            if not application.mortgage_lender:
                application.mortgage_lender = mortgage_lender
                application.save()
                return Response(serializer.validated_data, status=status.HTTP_201_CREATED)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
