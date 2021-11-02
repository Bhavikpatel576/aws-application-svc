from django.db import models

from utils.models import CustomBaseModelMixin
from utils.salesforce_model_mixin import SalesforceModelMixin


class MortgageLender(CustomBaseModelMixin, SalesforceModelMixin):
    # Salesforce Fields
    LENDER_FIRST_NAME_FIELD = 'Lender_First_Name__c'
    LENDER_LAST_NAME_FIELD = 'Lender_Last_Name__c'
    LENDER_FULL_NAME_FIELD = 'Lender_Full_Name__c'
    LENDER_PHONE_FIELD = 'Lender_Phone__c'
    LENDER_EMAIL_FIELD = 'Lender_Email__c'
    
    # Model Fields
    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)

    def is_complete(self):
        return self.name and self.email

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

    def salesforce_field_mapping(self):
        return {
            self.LENDER_EMAIL_FIELD: self.email,
            self.LENDER_PHONE_FIELD: self.phone,
            self.LENDER_FIRST_NAME_FIELD: self.get_first_name(),
            self.LENDER_LAST_NAME_FIELD: self.get_last_name()
        }
