from enum import Enum

from django.db import models

from utils.models import CustomBaseModelMixin
from application.models.offer import PropertyType, ContractType

class BuyingState(str, Enum):
    TX = 'TX',
    GA = 'GA',


class ContractTemplate(CustomBaseModelMixin):
    """
    Reference to get S3 filename from contract characteristics.
    """
    filename = models.CharField(max_length=1024, default=None, null=True)
    buying_state = models.CharField(max_length=2, choices=[(tag.value, tag.value) for tag in BuyingState])
    property_type = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in PropertyType])
    contract_type = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in ContractType])
    active = models.BooleanField(default=False)
