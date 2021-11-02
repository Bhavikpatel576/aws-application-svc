import logging

from api.v1_0_0.serializers.offer_serializer import OfferSerializer
from rest_framework import serializers

from api.v1_0_0.serializers.new_home_purchase_serializer import NewHomePurchaseSerializer
from api.v1_0_0.serializers.preapproval_serializer import PreApprovalSerializer
from application.models.application import Application
from application.models.loan import Loan
from .current_home_serializers import CurrentHomeSerializer
from .internal_support_user_serializer import InternalSupportSerializer
from .loan_serializer import LoanSerializer
from .application_serializers import CustomerSerializer


logger = logging.getLogger(__name__)


class UserApplicationSerializer(serializers.ModelSerializer):
    new_home_purchase = NewHomePurchaseSerializer()
    preapproval = PreApprovalSerializer()
    current_home = CurrentHomeSerializer(read_only=True)
    customer = CustomerSerializer()
    cx_manager = InternalSupportSerializer()
    loan_advisor = InternalSupportSerializer()
    offers = OfferSerializer(many=True)
    loan = serializers.SerializerMethodField()
    approval_specialist = InternalSupportSerializer()

    class Meta:
        model = Application
        fields = ['id', 'new_home_purchase', 'stage', 'preapproval', 'current_home', 'loan_advisor', 'cx_manager',
                  'product_offering', 'customer', 'mortgage_status', 'hw_mortgage_candidate', 'offers',
                  'apex_partner_slug', 'new_service_agreement_acknowledged_date', 'loan', 'needs_lender', 'approval_specialist']
        read_only_fields = ('id', 'new_service_agreement_acknowledged_date', 'loan')

    def get_loan(self, obj):
        loan_queryset = Loan.objects.filter(application_id=obj.id)\
            .exclude(status__in=['Recommended for Denial', 'Denial Signed-Off', 'Denial Communicated', 'Withdrawn'])\
            .order_by('-created_at')

        if len(loan_queryset) > 1:
            logger.info(f"application {obj.id} has more than one loan", extra=dict(logger='application',
                                                                                   method='get_loan',
                                                                                   type='more_than_one_loan_for_app'))

        data = LoanSerializer(loan_queryset.first()).data

        return data
