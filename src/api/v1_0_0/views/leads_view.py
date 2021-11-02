from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from api.v1_0_0.serializers.real_estate_lead_serializer import RealEstateLeadSerializer


class LeadViewSet(viewsets.ModelViewSet):
    http_method_names = ['post']
    serializer_class = RealEstateLeadSerializer
    permission_classes = [AllowAny]
