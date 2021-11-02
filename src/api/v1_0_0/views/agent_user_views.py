import logging

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from api.v1_0_0 import serializers
from api.v1_0_0.permissions import IsApplicationBuyingAgent, IsPricingAgent
from api.v1_0_0.serializers.acknowledgement_serializer import \
    AcknowledgementSerializer
from application.models.application import Application
from application.models.pricing import Pricing
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)

class AgentUserApplicationViewSet(GenericViewSet):
    http_method_names = ['get', 'put']
    serializer_class = serializers.UserApplicationSerializer
    permission_classes = [IsAuthenticated, IsApplicationBuyingAgent]

    def get_queryset(self, application_id=None):
        if not application_id: 
            return Application.objects.filter(buying_agent__email__iexact=self.request.user.email)
        return get_object_or_404(Application, id=application_id)

    @action(methods=['get'], detail=False, url_path='applications/active', permission_classes=[IsAuthenticated, IsApplicationBuyingAgent])
    def get_active_applications(self, request):
        applications = self.get_queryset()
        serializer = self.get_serializer(applications, many=True)
        return Response(serializer.data)
    
    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated, IsApplicationBuyingAgent])
    def applications(self, request):
        applications = self.get_queryset()
        active_applications = applications.filter(filter_status=[])
        archived_applications = applications.filter(filter_status=['Archived'])

        active_applications = self.get_serializer(active_applications, many=True)
        archived_applications = self.get_serializer(archived_applications, many=True) 
        return Response({'active': active_applications.data, 'archived': archived_applications.data})

    @action(methods=['get'], detail=False, url_path=r'applications/(?P<pk>[^/.]+)/detail', permission_classes=[IsAuthenticated, IsApplicationBuyingAgent])
    def get_application_detail(self, request, pk=None):  
        application = self.get_object()
        serializer = self.get_serializer(application)
        return Response(serializer.data)

    @action(methods=['get'], detail=False, url_path=r'applications/(?P<pk>[^/.]+)/acknowledgements', serializer_class=AcknowledgementSerializer)
    def get_application_acknowledgements(self, request, pk):
        serializer = self.get_serializer(self.get_object().acknowledgements.filter(is_acknowledged=True,
                                                                                   disclosure__active=True), many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path=r'applications/(?P<pk>[^/.]+)/acknowledgements/all-active', serializer_class=AcknowledgementSerializer)
    def get_all_application_acknowledgements(self, request, pk):
        serializer = self.get_serializer(self.get_object().acknowledgements.filter(disclosure__active=True), many=True)
        return Response(serializer.data)
    
    @action(methods=['put'], detail=False, url_path=r'applications/(?P<pk>[^/.]+)/archive',
            permission_classes=[IsAuthenticated, IsPricingAgent])
    def put_archive_application(self, *args, **kwargs):
        application_id = self.kwargs.get('pk')
        application = self.get_queryset(application_id=application_id)
        
        if Application.FilterStatus.ARCHIVED in application.filter_status:
            return Response(status=200, data={"message": f"Application {application_id} already archived"})
        application.filter_status.append(Application.FilterStatus.ARCHIVED)
        application.save()
        return Response(status=200, data={"message": f"Application {application_id} marked as archived"})

    @action(methods=['put'], detail=False, url_path=r'applications/(?P<pk>[^/.]+)/unarchive',
            permission_classes=[IsAuthenticated, IsPricingAgent])
    def put_unarchive_application(self, *args, **kwargs):
        application_id = self.kwargs.get('pk')
        application = self.get_queryset(application_id=application_id)
        if len(application.filter_status) == 0:
            return Response(status=200, data={"message": f"Application {application_id} is already not archived"})
        application.filter_status.remove(Application.FilterStatus.ARCHIVED)
        application.save()
        return Response(status=200, data={"message": f"Application {application_id} marked unarchived"})

class AgentUserQuoteViewSet(GenericViewSet):
    http_method_names = ['get', 'put']
    serializer_class = serializers.PricingSerializer
    permission_classes = [IsAuthenticated, IsPricingAgent]

    def get_queryset(self, quote_id=None):
        if not quote_id:
            return Pricing.objects.filter(agent__email=self.request.user.email)
        return get_object_or_404(Pricing, id=quote_id)

    @action(methods=['get'], detail=False, url_path='quotes/active', permission_classes=[IsAuthenticated, IsPricingAgent])
    def get_active_application(self, request):
        quotes = self.get_queryset()
        serializer = self.get_serializer(quotes, many=True)
        return Response(serializer.data)
    
    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated, IsPricingAgent])
    def quotes(self, request):
        quotes = self.get_queryset()
        active_quotes = quotes.filter(filter_status=[])   
        active_quotes = self.get_serializer(active_quotes, many=True)

        return Response({'active': active_quotes.data})

    @action(methods=['put'], detail=False, url_path=r'quotes/(?P<quote_id>[a-zA-Z0-9/.-]{1,})/archive',
            permission_classes=[IsAuthenticated, IsPricingAgent])
    def put_archive_quote(self, *args, **kwargs):
        quote_id = self.kwargs.get('quote_id')
        quote = self.get_queryset(quote_id=quote_id)
        if Pricing.FilterStatus.ARCHIVED.name in quote.filter_status:
            return Response(status=200, data={"message": f"Quote {quote_id} already archived"})
        quote.filter_status.append(Pricing.FilterStatus.ARCHIVED.name)
        quote.save()
        return Response(status=200, data={"message": f"Quote {quote_id} marked as archived"})
