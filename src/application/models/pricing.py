import logging
from enum import Enum

from django.conf import settings
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models

from application.models.address import Address
from application.models.application import Application, ProductOffering
from application.models.real_estate_agent import RealEstateAgent
from utils.models import CustomBaseModelMixin
from utils.salesforce import homeward_salesforce, SalesforceObjectType
from utils.salesforce_model_mixin import SalesforceModelMixin

logger = logging.getLogger(__name__)


class Pricing(CustomBaseModelMixin, SalesforceModelMixin):
    
    class FilterStatus(str, Enum):
        ARCHIVED = 'Archived'
        
    """
    inputs!
    """
    buying_location = models.ForeignKey(Address, on_delete=models.DO_NOTHING, related_name='buying_location_pricing',
                                        blank=True, null=True)
    selling_location = models.ForeignKey(Address, on_delete=models.DO_NOTHING, related_name='selling_location_pricing',
                                         blank=True, null=True)
    min_price = models.PositiveIntegerField()
    max_price = models.PositiveIntegerField()
    agents_company = models.TextField(blank=True, null=True)
    product_offering = models.TextField(default=ProductOffering.BUY_SELL.value)
    utm = JSONField(blank=True, null=True, default=dict)

    """
    outputs!
    """
    estimated_min_convenience_fee = models.DecimalField(max_digits=4, decimal_places=2)
    estimated_max_convenience_fee = models.DecimalField(max_digits=4, decimal_places=2)
    estimated_earnest_deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.0)
    estimated_min_rent_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    estimated_max_rent_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    agent_remarks = models.TextField(blank=True, null=True)
    agent = models.ForeignKey(RealEstateAgent, blank=True, null=True, on_delete=models.DO_NOTHING)
    application = models.OneToOneField(Application, blank=True, null=True, on_delete=models.DO_NOTHING)
    questionnaire_response_id = models.CharField(max_length=255, blank=True, null=True)
    actions = ArrayField(models.CharField(max_length=10), default=list)
    agent_situation = models.TextField(blank=True, null=True)
    filter_status = ArrayField(models.CharField(max_length=10, choices=[('Archived', 'Archived')], blank=True, null=True), default=list)
    shared_on_date = models.DateTimeField(blank=True, null=True, verbose_name='shared on')

    """
    other things!
    """
    salesforce_id = models.TextField(blank=True, null=True)

    salesforce_object_type = SalesforceObjectType.QUOTE

    def salesforce_field_mapping(self):
        base_payload = {
            "Agent_Remarks__c": self.agent_remarks,
            "Agent_Situation__c": self.agent_situation,
            "Estimated_EMD__c": self.estimated_earnest_deposit_percentage,
            "Maximum_Convenience_Fee__c": self.estimated_max_convenience_fee,
            "Maximum_Price__c": self.max_price,
            "Maximum_Rent_Amount__c": self.estimated_max_rent_amount,
            "Minimum_Convenience_Fee__c": self.estimated_min_convenience_fee,
            "Minimum_Price__c": self.min_price,
            "Minimum_Rent_Amount__c": self.estimated_min_rent_amount,
            "Saved__c": "saved" in self.actions,
            "Shared__c": "shared" in self.actions,
        }

        if self.buying_location:
            base_payload.update({
                "Property_City__c": self.buying_location.city,
                "Property_State__c": self.buying_location.state,
                "Property_Street__c": self.buying_location.street,
                "Property_Zip__c": self.buying_location.zip,
            })

        if self.agent:
            if self.agent.sf_id:
                base_payload.update({
                    "Agent__c": self.agent.sf_id,
                })
            elif self.agent.email:
                base_payload.update({
                    "Agent_Email__c": self.agent.email
                })

            if self.application:
                base_payload.update({
                    "Customer__c": self.application.new_salesforce
                })

            if self.questionnaire_response_id:
                base_payload.update({
                    "Agent_Quote_Resume_Link__c": self.get_resume_link()
                })

        return base_payload

    def calculate_pricing(self):
        self.hacky_calculate_min_convenience_fee()
        self.calculate_max_convenience_fee()
        self.calculate_earnest_money_deposit_percentage()
        self.calculate_rent()

    def calculate_earnest_money_deposit_percentage(self):
        if settings.USE_NEW_PRICING_UPDATES:
            if self.product_offering == ProductOffering.BUY_SELL:
                self.calculate_buy_sell_earnest_money_deposit_percentage()
            elif self.product_offering == ProductOffering.BUY_ONLY:
                self.calculate_buy_only_earnest_money_deposit_percentage()
            else:
                raise NotImplementedError(f"unable to calculate EMD for offering {self.product_offering}")
        else:
            if self.product_offering == ProductOffering.BUY_SELL:
                self._old_calculate_buy_sell_earnest_money_deposit_percentage()
            elif self.product_offering == ProductOffering.BUY_ONLY:
                self._old_calculate_buy_only_earnest_money_deposit_percentage()
            else:
                raise NotImplementedError(f"unable to calculate EMD for offering {self.product_offering}")

    def _old_calculate_buy_sell_earnest_money_deposit_percentage(self):
        if self.max_price < 1000000:
            self.estimated_earnest_deposit_percentage = 2.0
        elif 1000000 <= self.max_price < 1500000:
            self.estimated_earnest_deposit_percentage = 3.0
        elif 1500000 <= self.max_price < 2500000:
            self.estimated_earnest_deposit_percentage = 4.0
        elif 2500000 <= self.max_price:
            self.estimated_earnest_deposit_percentage = 5.0
        else:
            raise NotImplementedError(f"unable to map purchase price {self.max_price} to EMD amount")

    def calculate_buy_sell_earnest_money_deposit_percentage(self):
        if self.max_price < 1000000:
            self.estimated_earnest_deposit_percentage = 2.0
        elif 1000000 <= self.max_price:
            self.estimated_earnest_deposit_percentage = 4.0
        else:
            raise NotImplementedError(f"unable to map purchase price {self.max_price} to EMD amount")

    def _old_calculate_buy_only_earnest_money_deposit_percentage(self):
        if self.max_price < 1000000:
            self.estimated_earnest_deposit_percentage = 3.0
        elif 1000000 <= self.max_price < 1500000:
            self.estimated_earnest_deposit_percentage = 4.0
        elif 1500000 <= self.max_price < 2500000:
            self.estimated_earnest_deposit_percentage = 5.0
        elif 2500000 <= self.max_price:
            self.estimated_earnest_deposit_percentage = 6.0
        else:
            raise NotImplementedError(f"unable to map purchase price {self.max_price} to EMD amount")

    def calculate_buy_only_earnest_money_deposit_percentage(self):
        if self.max_price < 1000000:
            self.estimated_earnest_deposit_percentage = 2.0
        elif 1000000 <= self.max_price:
            self.estimated_earnest_deposit_percentage = 4.0
        else:
            raise NotImplementedError(f"unable to map purchase price {self.max_price} to EMD amount")

    def calculate_min_convenience_fee(self):
        if self.product_offering == ProductOffering.BUY_SELL:
            self.calculate_buy_sell_min_convenience_fee()
        elif self.product_offering == ProductOffering.BUY_ONLY:
            self.calculate_buy_only_min_convenience_fee()
        else:
            raise NotImplementedError(f"unable to calculate min convenience fee for offering {self.product_offering}")

    def calculate_buy_sell_min_convenience_fee(self):
        min_convenience_fee = 1.4

        if self.agent:
            if self.agent.brokerage and self.agent.brokerage.name == 'Realty Austin':
                min_convenience_fee -= 0.4

        if self.buying_location.state.upper() == 'GA':
            if self.max_price >= 300000:
                min_convenience_fee = 1.4
            else:
                min_convenience_fee = 1.9

        self.estimated_min_convenience_fee = min_convenience_fee

    def calculate_buy_only_min_convenience_fee(self):
        min_convenience_fee = 0.0

        self.estimated_min_convenience_fee = min_convenience_fee

    def hacky_calculate_min_convenience_fee(self):
        if self.agents_company:
            if self.agents_company == 'ra':
                self.estimated_min_convenience_fee = 1.0
            elif self.agents_company == '8z':
                self.estimated_min_convenience_fee = 1.9
            else:
                self.calculate_min_convenience_fee()
        else:
            self.calculate_min_convenience_fee()

    def calculate_max_convenience_fee(self):
        if self.product_offering == ProductOffering.BUY_SELL:
            self.calculate_buy_sell_max_convenience_fee()
        elif self.product_offering == ProductOffering.BUY_ONLY:
            self.calculate_buy_only_max_convenience_fee()
        else:
            raise NotImplementedError(f"unable to calculate max convenience fee for offering {self.product_offering}")

    def calculate_buy_sell_max_convenience_fee(self):
        max_convenience_fee = 1.9

        if self.buying_location.state.upper() == 'GA':
            if self.min_price >= 300000:
                max_convenience_fee = 2.4
            elif self.min_price >= 0:
                max_convenience_fee = 2.9

        self.estimated_max_convenience_fee = max_convenience_fee

    def calculate_buy_only_max_convenience_fee(self):
        max_convenience_fee = 1.9

        self.estimated_max_convenience_fee = max_convenience_fee

    def calculate_rent(self):
        if settings.USE_NEW_PRICING_UPDATES:
            if self.product_offering == ProductOffering.BUY_SELL or self.product_offering == ProductOffering.BUY_ONLY:
                self.calculate_standard_product_daily_rent()
            else:
                raise NotImplementedError(f"unable to calculate rent for product offering {self.product_offering}")
        else:
            if self.product_offering == ProductOffering.BUY_SELL:
                self.calculate_buy_sell_rent()
            elif self.product_offering == ProductOffering.BUY_ONLY:
                self.calculate_buy_only_rent()
            else:
                raise NotImplementedError(f"unable to calculate rent for product offering {self.product_offering}")

    def calculate_buy_only_rent(self):
        self.estimated_min_rent_amount = None
        self.estimated_max_rent_amount = None

    def calculate_buy_sell_rent(self):
        self.estimated_min_rent_amount = round(self.min_price * 0.07 / 12, 2)
        self.estimated_max_rent_amount = round(self.max_price * 0.07 / 12, 2)

    def get_monthly_rent_percentage(self):
        if self.max_price <= 1000000:
            return 0.0072
        else:
            return 0.0055

    def calculate_standard_product_daily_rent(self):
        monthly_rent_percentage = self.get_monthly_rent_percentage()
        self.estimated_min_rent_amount = round((self.min_price * monthly_rent_percentage) / 31, 2)
        self.estimated_max_rent_amount = round((self.max_price * monthly_rent_percentage) / 31, 2)

    def save(self, *args, **kwargs):
        if self.buying_location and self.min_price is not None and self.max_price is not None:
            self.calculate_pricing()
        try:
            if self.salesforce_id:
                homeward_salesforce.update_salesforce_object(self.salesforce_id,
                                                             self.to_salesforce_representation(),
                                                             self.salesforce_object_type)
            else:
                salesforce_id = homeward_salesforce.create_new_salesforce_object(self.to_salesforce_representation(),
                                                                                 self.salesforce_object_type)
                self.salesforce_id = salesforce_id
        except Exception as e:
            logger.error("Failed sending quote to salesforce", exc_info=e, extra=dict(
                type="failed_sending_quote_to_salesforce",
                pricing_id=self.id
            ))
        return super(Pricing, self).save(*args, **kwargs)

    def get_resume_link(self):
        if self.questionnaire_response_id:
            return f'{settings.ONBOARDING_BASE_URL}estimates/resume/{self.questionnaire_response_id}'
        else:
            logger.warning("Can't build resume link for pricing object because of missing questionnaire_response_id",
                           extra=dict(
                               type="cant_build_resume_link_pricing_missing_questionnaire_response_id",
                               pricing_id=self.id
                           ))
            raise AttributeError(f"failed building resume link for pricing object {self.id}")

    def customer_email(self):
        if self.application:
            return self.application.customer.email