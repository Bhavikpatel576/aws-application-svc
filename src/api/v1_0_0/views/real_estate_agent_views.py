from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from api.v1_0_0 import serializers
from application.models.real_estate_agent import RealEstateAgent


class RealEstateAgentViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'put', 'delete']
    serializer_class = serializers.RealEstateAgentSerializer
    permission_classes = (IsAdminUser,)
    queryset = RealEstateAgent.objects.all()
    lookup_field = "sf_id"

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except Http404:
            return self.create(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='lookup', permission_classes=[AllowAny])
    def lookup(self, request):
        email = request.query_params.get('email')
        phone = request.query_params.get('phone')

        if email is None:
            return HttpResponseBadRequest('email query param not provided')

        agent = RealEstateAgent.objects.filter(is_certified=True, email=email).first()
        if agent is None and phone:
            agent = RealEstateAgent.objects.filter(is_certified=True, phone=phone).first()
        if agent is None:
            agent = RealEstateAgent.objects.filter(email=email).first()
        if agent is None and phone:
            agent = RealEstateAgent.objects.filter(phone=phone).first()
        if agent is None:
            return Response(status=204)

        return Response(self.get_serializer(agent).data)


class CertifiedAgentViewSet(viewsets.ModelViewSet):
    http_method_names = ['get']
    serializer_class = serializers.CertifiedAgentSerializer
    permission_classes = (AllowAny,)

    def get_object(self):
        return get_object_or_404(RealEstateAgent, is_certified=True, pk=self.kwargs['pk'])
