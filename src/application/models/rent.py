from datetime import datetime
from decimal import Decimal
from enum import Enum

from django.db import models

from utils.models import CustomBaseModelMixin


class RentType(str, Enum):
    MONTHLY = 'Monthly'
    DEFERRED = 'Deferred'
    TWO_MONTHS_DEFERRED = 'Two mos deferred then monthly'


class Rent(CustomBaseModelMixin):
    # Salesforce Fields
    CUSTOMER_FIELD = 'Customer__c'
    RENT_PAYMENT_TYPE_FIELD = 'Rent_Type__c'
    RENT_DAILY_RENTAL_RATE = 'Daily_Rent__c'
    RENT_MONTHLY_RENTAL_RATE = 'New_Home_Rent_Amount_Per_Month__c'
    RENT_STOP_DATE = 'HW_Stop_Rent_Date__c'
    RENT_TOTAL_WAIVED_RENT = 'Homeward_Credit_Amount__c'
    RENT_TOTAL_LEASEBACK_CREDIT = 'Leaseback_Credit_Amount__c'

    # Model Fields
    type = models.CharField(max_length=50)
    daily_rental_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_months_one_and_two = models.DecimalField(max_digits=10, decimal_places=2)
    total_waived_rent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_leaseback_credit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stop_rent_date = models.DateField(blank=True, null=True)

    @property
    def accrued_rent(self):
        if not self.new_home_purchase.homeward_purchase_close_date:
            return

        # show accrued rent if there is no customer purchase close date
        # or if the customer purchase close date is beyond today's date
        if not self.new_home_purchase.customer_purchase_close_date \
                or self.new_home_purchase.customer_purchase_close_date > datetime.now().date():
            days = (datetime.now().date() - self.new_home_purchase.homeward_purchase_close_date).days + 1
            return round(days * self.daily_rental_rate, 2)

        # if customer purchase close date is on or before today's date, show accrued rent for time diff
        if self.new_home_purchase.customer_purchase_close_date <= datetime.now().date():
            days = (self.new_home_purchase.customer_purchase_close_date - self.new_home_purchase.homeward_purchase_close_date).days + 1
            return round(days * self.daily_rental_rate, 2)

    @property
    def future_rent_to_be_charged(self):
        # only show future rent if there is a customer purchase close date beyond today's date
        if self.new_home_purchase.customer_purchase_close_date:
            if self.new_home_purchase.customer_purchase_close_date > datetime.now().date():
                days = (self.new_home_purchase.customer_purchase_close_date - datetime.now().date()).days
                return round(days * self.daily_rental_rate, 2)

    @property
    def estimated_total_rent(self):
        if not self.accrued_rent and not self.future_rent_to_be_charged:
            return

        accrued_rent = self.accrued_rent if self.accrued_rent else Decimal('0')
        future_rent_to_be_charged = self.future_rent_to_be_charged if self.future_rent_to_be_charged else Decimal('0')
        total_waived_rent = self.total_waived_rent if self.total_waived_rent else Decimal('0')
        total_leaseback_credit = self.total_leaseback_credit if self.total_leaseback_credit else Decimal('0')

        return round((accrued_rent + future_rent_to_be_charged) - total_waived_rent - total_leaseback_credit, 2)

    @property
    def estimated_total_rent_before_credits(self):
        if not self.accrued_rent and not self.future_rent_to_be_charged:
            return

        accrued_rent = self.accrued_rent if self.accrued_rent else Decimal('0')
        future_rent_to_be_charged = self.future_rent_to_be_charged if self.future_rent_to_be_charged else Decimal('0')
        return round((accrued_rent + future_rent_to_be_charged), 2)
