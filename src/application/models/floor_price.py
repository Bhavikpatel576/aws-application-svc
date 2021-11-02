from enum import Enum

from django.db import models

from utils.models import CustomBaseModelMixin


class FloorPriceType(str, Enum):
    REQUIRED = 'Required'
    NONE = 'No Floor Price'
    BUYER_ONLY = 'Buyer Only'


class FloorPrice(CustomBaseModelMixin):
    # Salesforce Fields
    FLOOR_PRICE_TYPE_FIELD = 'Floor_Price_Type__c'
    FLOOR_PRICE_AMOUNT_FIELD = 'Floor_Price_Amount__c'
    PRELIMINARY_FLOOR_PRICE_FIELD = 'Prelim_Floor_Price__c'

    # Model Fields
    type = models.CharField(max_length=50)
    preliminary_amount = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
