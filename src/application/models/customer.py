from django.db import models

from utils.models import CustomBaseModelMixin
from utils.salesforce_model_mixin import SalesforceModelMixin

class Customer(CustomBaseModelMixin, SalesforceModelMixin):
    # Salesforce Fields
    CO_BORROWER_EMAIL_FIELD: str = 'Co_borrower_Email__c'
    FIRST_NAME_FIELD: str = 'FirstName'
    LAST_NAME_FIELD = 'LastName'
    PHONE_FIELD = 'Phone'
    EMAIL_FIELD: str = 'PersonEmail'

    # Model Fields
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50)
    co_borrower_email = models.EmailField(null=True, blank=True)
    
    def __str__(self):
        """
        Customer object representation
        """
        return "{}".format(self.name)

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
            self.EMAIL_FIELD: self.email,
            self.PHONE_FIELD: self.phone,
            self.FIRST_NAME_FIELD: self.get_first_name(),
            self.LAST_NAME_FIELD: self.get_last_name()
        }
