from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.salesforce import sync_transaction_record_from_salesforce


class TransactionView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        saleforce_records = request.data
        if isinstance(saleforce_records, list):
            for record in saleforce_records:
                sync_transaction_record_from_salesforce.delay(record)

        return Response(status=status.HTTP_200_OK)
