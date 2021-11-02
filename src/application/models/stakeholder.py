from django.db import IntegrityError, models
from django.db.models.fields import IntegerField

from application.models.application import Application
from utils.models import CustomBaseModelMixin
from application.models.stakeholder_type import StakeholderType


class Stakeholder(CustomBaseModelMixin):
    """Stakeholders represent interested parties or contacts of an application"""
    # Model Fields
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="stakeholders")
    email = models.TextField(max_length=50)
    type = models.TextField(max_length=50,
                            choices=[(tag.value, tag.value) for tag in StakeholderType])
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['application'],
                                    condition=models.Q(type=StakeholderType.TRANSACTION_COORDINATOR),
                                    name='unique_transaction_coordinator_application')
            ]
