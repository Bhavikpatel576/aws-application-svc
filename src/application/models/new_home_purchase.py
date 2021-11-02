from django.db import models

from enum import Enum

from application.models.address import Address
from application.models.rent import Rent
from utils.models import CustomBaseModelMixin


class NewHomePurchase(CustomBaseModelMixin):
    # Salesforce Fields
    TRANSACTION_RECORD_TYPE = 'Record_Type_Name__c'
    NEW_HOME_PURCHASE_CLOSE_DATE = 'Closing_Date__c'
    OPTION_END_DATE_FIELD = 'Post_Option_Stage_Date__c'
    NEW_HOME_PURCHASE_STATUS = 'Status__c'
    CONTRACT_PRICE_TRANSACTION_FIELD = 'Contract_Price__c'
    EARNEST_DEPOSIT_PERCENTAGE_FIELD = 'EMD__c'
    REASSIGNED_CONTRACT_FIELD = 'Reassigned_Contract__c'

    # TODO Remove after transition (CLOS-219)
    HOMEWARD_PURCHASE_CLOSE_DATE_FIELD = 'Homeward_Purchase_Close_Date__c'
    CUSTOMER_PURCHASE_CLOSE_DATE_FIELD = 'Scheduled_Close_Date__c'
    CONTRACT_PRICE_FIELD = 'New_Home_Contract_Price__c'

    # Model Fields
    rent = models.OneToOneField(Rent, on_delete=models.CASCADE, blank=True, null=True, related_name='new_home_purchase')
    option_period_end_date = models.DateField(blank=True, null=True)
    homeward_purchase_close_date = models.DateField(blank=True, null=True)
    homeward_purchase_status = models.TextField(blank=True, null=True)
    contract_price = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    earnest_deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    is_reassigned_contract = models.BooleanField(default=False)
    customer_purchase_close_date = models.DateField(blank=True, null=True)
    customer_purchase_status = models.TextField(blank=True, null=True)
    address = models.ForeignKey(Address, on_delete=models.CASCADE, blank=True, null=True)
