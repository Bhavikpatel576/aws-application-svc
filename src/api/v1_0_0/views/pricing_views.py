from datetime import datetime
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.v1_0_0.serializers import PricingSerializer
from application.models.pricing import Pricing


class PricingViewSet(mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    http_method_names = ['get', 'post', 'put', 'patch']
    permission_classes = [AllowAny]
    queryset = Pricing.objects.all()
    serializer_class = PricingSerializer

    @action(methods=['post'], detail=True, url_path='actions')
    def add_action(self, request, pk=None):
        pricing = self.get_object()
        actions = request.data.get('actions')

        for action in actions:
            pricing.actions.append(action)
            
        if "shared" in actions:
            pricing.shared_on_date = datetime.now()
            
        pricing.save()

        return Response(self.get_serializer(pricing).data)
