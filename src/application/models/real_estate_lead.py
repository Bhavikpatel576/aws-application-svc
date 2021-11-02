from django.db import models

from application.models.application import HomeBuyingStage, Application
from application.models.customer import Customer
from application.models.address import Address, SalesforceAddressType
from utils.models import CustomBaseModelMixin
from utils.salesforce_model_mixin import SalesforceModelMixin, SalesforceObjectType


class RealEstateLead(CustomBaseModelMixin, SalesforceModelMixin):
    # Salesforce Fields
    NEEDS_BUYING_AGENT_FIELD = 'Needs_Buying_Agent__c'
    NEEDS_LISTING_AGENT_FIELD = 'Needs_Listing_Agent__c'
    CUSTOMER_REPORTED_STAGE_FIELD = 'Customer_reported_stage__c'

    # Model Fields
    customer: Customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    address: Address = models.ForeignKey(Address, on_delete=models.SET_NULL, blank=True, null=True,
                                         related_name='market_location')
    needs_buying_agent: bool = models.BooleanField()
    needs_listing_agent: bool = models.BooleanField()
    home_buying_stage: str = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in
                                                                      HomeBuyingStage])
    def salesforce_field_mapping(self):
        return {
            self.NEEDS_BUYING_AGENT_FIELD: self.needs_buying_agent,
            self.NEEDS_LISTING_AGENT_FIELD: self.needs_listing_agent,
            self.CUSTOMER_REPORTED_STAGE_FIELD: self.home_buying_stage,
            Application.RECORD_TYPE_ID_FIELD: Application.RECORD_TYPE_ID_VALUE
        }

    def salesforce_object_type(self):
        return SalesforceObjectType.ACCOUNT

    def to_salesforce_representation(self):
        payload = super().to_salesforce_representation()
        payload.update(self.customer.to_salesforce_representation())
        payload.update(self.address.to_salesforce_representation(SalesforceAddressType.BILLING_ADDRESS))
        return payload
