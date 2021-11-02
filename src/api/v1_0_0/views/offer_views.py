from datetime import datetime

from celery.exceptions import TimeoutError
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response

from api.v1_0_0.permissions import IsApplicationBuyingAgent
from api.v1_0_0.serializers.offer_serializer import OfferSerializer
from application.models.application import ProductOffering
from application.models.offer import Offer
from application.tasks import queue_offer_contract
from utils.date_restrictor import calculate_restricted_dates
from utils.date_restrictor import get_earliest_close_date, get_latest_close_date
from utils.salesforce import sync_offer_record_from_salesforce


class OfferViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'patch']
    serializer_class = OfferSerializer
    permission_classes = [IsAuthenticated, IsApplicationBuyingAgent]
    queryset = Offer.objects.all()

    @action(methods=['post'], detail=False, url_path='salesforce/bulk', permission_classes=[IsAdminUser])
    def bulk_salesforce(self, request):
        saleforce_records = request.data
        if isinstance(saleforce_records, list):
            for record in saleforce_records:
                sync_offer_record_from_salesforce.delay(record)

        return Response(status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True, url_path='contract')
    def get_offer_contract(self, request, pk):
        try:
            offer = Offer.objects.get(id=pk)
        except Offer.DoesNotExist:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        if offer.application.buying_agent.email != request.user.email:
            return Response({}, status=status.HTTP_403_FORBIDDEN)

        task = queue_offer_contract.apply_async([offer.id], task_id=str(offer.id))

        try:
            url = task.get(interval=0.5, timeout=25)
        except TimeoutError:
            return Response({}, status=status.HTTP_408_REQUEST_TIMEOUT)

        return Response({'url': url}, status=status.HTTP_200_OK) if url else Response({},
                                                                                      status=status.HTTP_404_NOT_FOUND)

    @action(methods=['get'], detail=True, url_path='offer-restricted-dates')
    def closing_restricted_dates(self, request, pk):

        offer = get_object_or_404(Offer, pk=pk)

        args = (ProductOffering(offer.application.product_offering), reference_date := datetime.now())
        date_response = {'earliest_possible_close_date': get_earliest_close_date(*args).isoformat(),
                         'latest_possible_close_date': (end_date := get_latest_close_date(reference_date)).isoformat(),
                         'restricted_close_dates': [rd.isoformat() for rd in
                                              calculate_restricted_dates(reference_date.date(), end_date)]}

        return Response(date_response)

    @action(methods=['get'], detail=False, url_path='internal-restricted-dates', permission_classes=[AllowAny])
    def internal_closing_restricted_dates(self, request):
        """
        Endpoint used to generate the restricted dates from today onward, used internally to view capacity.

        :param request: the request object of the client
        :return: a start date (today), end date (18 months from now), and list of any daays were at capacity between
        the two dates.
        """
        start_date = datetime.now()
        end_date = get_latest_close_date(start_date)

        date_response = {
            'earliest_possible_close_date': start_date.date().isoformat(),
            'latest_possible_close_date': end_date.isoformat(),
            'restricted_close_dates': [rd.isoformat() for rd in calculate_restricted_dates(start_date.date(), end_date)]
        }

        return Response(date_response)
