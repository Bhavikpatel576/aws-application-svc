from django.http import Http404
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from api.v1_0_0.serializers.brokerage_serializers import BrokerageSerializer
from application.models.brokerage import Brokerage


class BrokerageViewSet(viewsets.ModelViewSet):
    http_method_names = ['put']
    serializer_class = BrokerageSerializer
    permisisions_classes = (IsAdminUser,)
    queryset = Brokerage.objects.all()
    lookup_field = "sf_id"

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Http404:
            return self.create(request, *args, **kwargs)
