from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from api.v1_0_0.serializers import NewHomePurchaseSerializer

from utils.salesforce import sync_customer_purchase_record_from_salesforce


class NewHomePurchaseViewSet(viewsets.GenericViewSet):
    http_method_names = ['post']
    serializer_class = NewHomePurchaseSerializer
    permission_classes = [IsAuthenticated]

    @action(methods=['post'], detail=False, url_path='salesforce', permission_classes=[IsAdminUser])
    def sync_customer_purchase_from_salesforce(self, request):
        saleforce_records = request.data
        if isinstance(saleforce_records, list):
            for record in saleforce_records:
                sync_customer_purchase_record_from_salesforce.delay(record)

        return Response(status=status.HTTP_200_OK)
