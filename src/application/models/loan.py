from django.db import models

from application.models.application import Application
from utils.models import CustomBaseModelMixin


class Loan(CustomBaseModelMixin):
    # Salesforce Fields
    BLEND_APPLICATION_ID_FIELD = 'Loan_Id__c'
    CUSTOMER_FIELD = 'Customer__c'
    LOAN_STATUS_FIELD = 'Status__c'
    SALESFORCE_ID_FIELD = 'Id'
    DENIAL_REASON_FIELD = 'Denial_Reason__c'
    BASE_CONVENIENCE_FEE_FIELD = 'Est_Base_Convenience_Fee__c'
    ESTIMATED_BROKER_CONVENIENCE_FEE_CREDIT_FIELD = 'Est_Brokerage_Conv_Fee_Credit__c'
    ESTIMATED_MORTGAGE_CONVENIENCE_FEE_CREDIT_FIELD = 'Est_Mortgage_Conv_Fee_Credit__c'
    ESTIMATED_DAILY_RENT = 'Est_Daily_Rent__c'
    ESTIMATED_MONTHLY_RENT = 'Est_Rent__c'
    ESTIMATED_EARNEST_DEPOSIT_PERCENTAGE = 'Est_EMD__c'

    # Model Fields
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="loans")
    blend_application_id = models.TextField(unique=True, null=False)
    status = models.TextField(blank=True, null=True)
    salesforce_id = models.TextField(unique=True, null=False)
    denial_reason = models.TextField(blank=True, null=True)
    base_convenience_fee = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    estimated_broker_convenience_fee_credit = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    estimated_mortgage_convenience_fee_credit = models.DecimalField(max_digits=10, decimal_places=2, blank=True,
                                                                    null=True)
    estimated_daily_rent = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    estimated_monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    estimated_earnest_deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
