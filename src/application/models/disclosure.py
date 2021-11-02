from enum import Enum

from django.db import models

from utils.models import CustomBaseModelMixin


class DisclosureType(str, Enum):
    TITLE = "title"
    MORTGAGE = "mortgage"
    SERVICE_AGREEMENT = "service_agreement"
    E_CONSENT = "e_consent"


class Disclosure(CustomBaseModelMixin):
    name = models.CharField(max_length=50)
    disclosure_type = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in DisclosureType])
    document_url = models.TextField()
    buying_state = models.CharField(max_length=50, null=True, blank=True)
    selling_state = models.CharField(max_length=50, null=True, blank=True)
    buying_agent_brokerage = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=False)
    product_offering = models.TextField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['buying_state', 'selling_state', 'buying_agent_brokerage', 'active',
                                            'product_offering'], name='unique_buying_selling_brokerage_active_offering')
        ]
