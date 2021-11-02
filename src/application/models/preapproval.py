from django.db import models

from utils.models import CustomBaseModelMixin


class PreApproval(CustomBaseModelMixin):
    # SalesforceFields
    PREAPPROVAL_AMOUNT_FIELD = 'Lender_Pre_Approval_Amount__c'
    ESTIMATED_DOWN_PAYMENT_AMOUNT_FIELD = 'Estimated_Down_Payment__c'
    VPAL_APPROVAL_DATE_FIELD = 'VPAL_Approved_Date__c'
    HW_MORTGAGE_CONDITIONS = 'HW_Mortgage_Conditions__c'

    # Model Fields
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    estimated_down_payment = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    vpal_approval_date = models.DateField(null=True, blank=True)
    hw_mortgage_conditions = models.TextField(blank=True, null=True)