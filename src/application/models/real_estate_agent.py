import re
from enum import Enum

from django.db import models
from django.db.models import Index

from application.models.brokerage import Brokerage
from utils.models import CustomBaseModelMixin
from utils.salesforce_model_mixin import SalesforceModelMixin, SalesforceObjectType



class AgentType(Enum):
    BUYING = 'buying'
    LISTING = 'listing'

class RealEstateAgent(CustomBaseModelMixin, SalesforceModelMixin):
    # Salesforce Fields
    NAME_FIELD: str = 'Name'

    # Salesforce listing agent fields
    LISTING_AGENT_FIRST_NAME_FIELD = 'Listing_Agent_First_Name__c'
    LISTING_AGENT_LAST_NAME_FIELD = 'Listing_Agent_Last_Name__c'
    LISTING_AGENT_PHONE_FIELD = 'Listing_Agent_Phone__c'
    LISTING_AGENT_EMAIL_FIELD = 'Listing_Agent_Email__c'
    LISTING_AGENT_COMPANY_FIELD = 'Listing_Agent_Company__c'
    LISTING_AGENT_ID_FIELD = 'Customer_List_Agent__c'

    # Salesforce buying agent fields
    BUYING_AGENT_FIRST_NAME_FIELD = 'Agent_First_Name__c'
    BUYING_AGENT_LAST_NAME_FIELD = 'Agent_Last_Name__c'
    BUYING_AGENT_PHONE_FIELD = 'Agent_Phone__c'
    BUYING_AGENT_EMAIL_FIELD = 'Agent_Email__c'
    BUYING_AGENT_COMPANY_FIELD = 'Agent_Company__c'
    BUYING_AGENT_ID_FIELD = 'Homeward_Customer_Broker__c'

    # Model Fields
    name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    company = models.CharField(blank=True, null=True, max_length=255)
    brokerage = models.ForeignKey(Brokerage, on_delete=models.DO_NOTHING, blank=True, null=True)
    self_reported_referral_source = models.CharField(blank=True, null=True, max_length=255)
    self_reported_referral_source_detail = models.CharField(blank=True, null=True, max_length=255)
    is_certified = models.BooleanField(default=False)
    sf_id = models.CharField(max_length=50, unique=True, null=True, default=None)

    class Meta:
        constraints = [
            # phone and sf_id must be unique if partner is certified
            models.UniqueConstraint(fields=['sf_id'], condition=models.Q(is_certified=True), name='unique_sf_id_certified_agent'),
            models.UniqueConstraint(fields=['phone'], condition=models.Q(is_certified=True), name='unique_phone_certified_agent'),
            # if is certified is True, sf_id and phone must not be null constraint
            models.CheckConstraint(check=models.Q(is_certified=False) | models.Q(phone__isnull=False) & ~models.Q(phone=''), name='required_phone_certified_agent'),
            models.CheckConstraint(check=models.Q(is_certified=False) | models.Q(sf_id__isnull=False) & ~models.Q(sf_id=''), name='required_sf_id_certified_agent'),
            models.CheckConstraint(check=models.Q(is_certified=False) | models.Q(email__isnull=False) & ~models.Q(email=''), name='required_email_certified_agent'),
        ]
        indexes = [
            Index(fields=['email']),
            Index(fields=['phone']),
            Index(fields=['sf_id']),
        ]

    def save(self, *args, **kwargs):
        # Agents phone numbers are standardized and stored as flat 10 digit numbers. (5555555555)
        if self.phone:
            str_phone = str(self.phone)
            self.phone = re.sub("[^0-9]", "", str_phone)[-10:]
        super(RealEstateAgent, self).save(*args, **kwargs)

    def has_name_and_email(self):
        return self.name and self.email

    def get_formatted_phone(self):
        if self.phone and len(self.phone) == 10:
            return "({}) {}-{}".format(self.phone[0:3], self.phone[3:6], self.phone[6:10])
        else:
            raise Exception("Cannot format phone: ", self.phone)

    def get_first_name(self):
        if self.name:
            names = self.name.split(" ")
            return names[0]
        return None

    def get_last_name(self):
        if self.name:
            names = self.name.split(" ")
            return " ".join(names[1::]) if len(names) > 1 else ''
        return None

    def listing_agent_field_mapping(self):
        return {
            self.LISTING_AGENT_EMAIL_FIELD: self.email,
            self.LISTING_AGENT_PHONE_FIELD: self.phone,
            self.LISTING_AGENT_COMPANY_FIELD: self.company,
            self.LISTING_AGENT_FIRST_NAME_FIELD: self.get_first_name(),
            self.LISTING_AGENT_LAST_NAME_FIELD: self.get_last_name(),
            self.LISTING_AGENT_ID_FIELD: self.sf_id
        }

    def buying_agent_field_mapping(self):
        return {
            self.BUYING_AGENT_EMAIL_FIELD: self.email,
            self.BUYING_AGENT_PHONE_FIELD: self.phone,
            self.BUYING_AGENT_COMPANY_FIELD: self.company,
            self.BUYING_AGENT_FIRST_NAME_FIELD: self.get_first_name(),
            self.BUYING_AGENT_LAST_NAME_FIELD: self.get_last_name(),
            self.BUYING_AGENT_ID_FIELD: self.sf_id
        }

    def salesforce_object_type(self):
        return SalesforceObjectType.ACCOUNT

    def to_salesforce_representation(self, agentType: AgentType):
        payload = {}
        if agentType is AgentType.LISTING:
            payload = super().to_salesforce_representation(self.listing_agent_field_mapping())
        else:
            payload = super().to_salesforce_representation(self.buying_agent_field_mapping())
        return payload
