from enum import Enum
from django.db import models

from utils.models import CustomBaseModelMixin
from utils.salesforce_model_mixin import SalesforceModelMixin, SalesforceModelException


class SalesforceAddressType(str, Enum):
    BILLING_ADDRESS = "billing address"
    OFFER_ADDRESS = "offer address"
    BUYING_LOCATION = "buying location"
    GENERAL_ADDRESS = "general address"

class Address(CustomBaseModelMixin, SalesforceModelMixin):
    # Salesforce fields
    BILLING_STREET_FIELD = 'BillingStreet'
    BILLING_CITY_FIELD = 'BillingCity'
    BILLING_STATE_FIELD = 'BillingState'
    BILLING_POSTAL_CODE_FIELD = 'BillingPostalCode'
    BILLING_UNIT_FIELD = 'Billing_Unit__c'

    HOME_SHOPPING_CITY_FIELD = 'Home_Shopping_City_Only__c'
    HOME_SHOPPING_STATE_FIELD = 'Home_Shopping_State__c'

    OFFER_ADDRESS_STREET_FIELD = "ShippingStreet"
    OFFER_ADDRESS_CITY_FIELD = "ShippingCity"
    OFFER_ADDRESS_STATE_FIELD = "ShippingState"
    OFFER_ADDRESS_ZIP_FIELD = "ShippingPostalCode"
    OFFER_ADDRESS_UNIT_FIELD = "Shipping_Unit__c"

    GENERAL_ADDRESS_STREET_FIELD = "Street__c"
    GENERAL_ADDRESS_CITY_FIELD = "City__c"
    GENERAL_ADDRESS_STATE_FIELD = "State__c"
    GENERAL_ADDRESS_ZIP_FIELD = "Zip__c"
    GENERAL_ADDRESS_UNIT_FIELD = "Unit__c"

    # Model Fields
    street = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    zip = models.CharField(max_length=255, blank=True, null=True)
    unit = models.CharField(max_length=255, blank=True, null=True)

    def get_inline_address(self):
        """
        Function to get address in one line.
        """
        address = ''
        address += '{}'.format(self.street) if self.street else ''
        address += ' {}, '.format(self.unit) if self.unit else ', '
        address += '{}, '.format(self.city) if self.city else ''
        address += '{}, '.format(self.state) if self.state else ''
        address += '{}'.format(self.zip) if self.zip else '.'
        return address

    def street_and_zip_address(self):
        """
        Function to get address street and zip needed for tx prefilled contract.
        """
        address = ''
        address += '{}'.format(self.street) if self.street else ''
        address += '{}'.format(" " + self.zip) if self.zip else '.'
        return address

    def street_and_city_address(self):
        """
        Function to get address street and city needed for ga prefilled contract.
        """
        address = ''
        address += '{}'.format(self.street) if self.street else ''
        address += '{}'.format(" " + self.city) if self.city else '.'
        return address

    def salesforce_billing_address_field_mapping(self):
        return {
            self.BILLING_STREET_FIELD: self.street,
            self.BILLING_UNIT_FIELD: self.unit,
            self.BILLING_CITY_FIELD: self.city,
            self.BILLING_STATE_FIELD: self.state,
            self.BILLING_POSTAL_CODE_FIELD: self.zip
        }

    def salesforce_offer_address_field_mapping(self):
        return {
            self.OFFER_ADDRESS_STREET_FIELD: self.street,
            self.OFFER_ADDRESS_UNIT_FIELD: self.unit,
            self.OFFER_ADDRESS_CITY_FIELD: self.city,
            self.OFFER_ADDRESS_STATE_FIELD: self.state,
            self.OFFER_ADDRESS_ZIP_FIELD: self.zip,
            self.HOME_SHOPPING_CITY_FIELD: self.city,
            self.HOME_SHOPPING_STATE_FIELD: self.state
        }

    def salesforce_general_address_field_mapping(self):
        return {
            self.GENERAL_ADDRESS_STREET_FIELD: self.street,
            self.GENERAL_ADDRESS_UNIT_FIELD: self.unit,
            self.GENERAL_ADDRESS_CITY_FIELD: self.city,
            self.GENERAL_ADDRESS_STATE_FIELD: self.state,
            self.GENERAL_ADDRESS_ZIP_FIELD: self.zip
        }

    def salesforce_buying_location_field_mapping(self):
        return {
            self.HOME_SHOPPING_CITY_FIELD: self.city,
            self.HOME_SHOPPING_STATE_FIELD: self.state
        }

    def to_salesforce_representation(self, address_type: SalesforceAddressType):
        payload = {}
        if address_type is SalesforceAddressType.OFFER_ADDRESS:
            payload = super().to_salesforce_representation(self.salesforce_offer_address_field_mapping())
        elif address_type is SalesforceAddressType.BILLING_ADDRESS:
            payload = super().to_salesforce_representation(self.salesforce_billing_address_field_mapping())
        elif address_type is SalesforceAddressType.BUYING_LOCATION:
            payload = super().to_salesforce_representation(self.salesforce_buying_location_field_mapping())
        elif address_type is SalesforceAddressType.GENERAL_ADDRESS:
            payload = super().to_salesforce_representation(self.salesforce_general_address_field_mapping())
        else:
            raise SalesforceModelException("Unknown Address Type")

        return payload
