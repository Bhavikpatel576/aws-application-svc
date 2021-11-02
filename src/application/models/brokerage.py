from django.db import models

from utils.models import CustomBaseModelMixin


class Brokerage(CustomBaseModelMixin):
    # Salesforce Fields
    BROKER_PARTNERSHIP_STATUS_FIELD: str = 'Broker_Partnership_Status__c'
    BROKERAGE_ID_FIELD = 'Brokerage__c'

    # Model Fields
    name = models.CharField(max_length=255)
    partnership_status = models.CharField(max_length=255, blank=True, null=True)
    logo_url = models.URLField(blank=True, null=True)
    sf_id = models.CharField(max_length=50, unique=True)
