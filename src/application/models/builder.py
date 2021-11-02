from django.db import models

from application.models.address import Address
from utils.models import CustomBaseModelMixin


class Builder(CustomBaseModelMixin):
    company_name = models.CharField(max_length=255, null=True, blank=True)
    representative_name = models.CharField(max_length=255, null=True, blank=True)
    representative_email = models.EmailField(blank=True, null=True)
    representative_phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.ForeignKey(Address, on_delete=models.CASCADE, null=True, blank=True)
    self_reported_referral_source = models.CharField(blank=True, null=True, max_length=255)
    self_reported_referral_source_detail = models.CharField(blank=True, null=True, max_length=255)
    is_certified = models.BooleanField(blank=True, null=True, default=False)
    sf_id = models.CharField(max_length=50, blank=True, null=True, default=None)

    # Salesforce Fields
    BUILDER_ADDRESS_FIELD = "Builder_address__c"
    BUILDER_COMPANY_FIELD = "Builder_Company__c"
    BUILDER_FIRST_NAME = "Builder_First_Name__c"
    BUILDER_LAST_NAME = "Builder_Last_Name__c"
    BUILDER_PHONE = "Builder_Phone__c"
    BUILDER_EMAIL = "Builder_Email__c"

    class Meta:
        constraints = [
            # phone and sf_id must be unique if partner is certified
            models.UniqueConstraint(fields=['representative_phone'], condition=models.Q(is_certified=True), name='unique_phone_certified_builder'),
            models.UniqueConstraint(fields=['sf_id'], condition=models.Q(is_certified=True), name='unique_sf_id_certified_builder'),
            # if is certified is True, sf_id and phone must not be null constraint
            models.CheckConstraint(check=models.Q(is_certified=False) | models.Q(representative_phone__isnull=False), name='required_sf_id_certified_builder'),
            models.CheckConstraint(check=models.Q(is_certified=False) | models.Q(sf_id__isnull=False), name='required_phone_certified_builder'),
        ]

    def get_first_name(self):
        if self.representative_name:
            names = self.representative_name.split(" ")
            return names[0]
        return None

    def get_last_name(self):
        if self.representative_name:
            names = self.representative_name.split(" ")
            return " ".join(names[1::]) if len(names) > 1 else ''
        return None
