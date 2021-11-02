from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models

from application.models.address import Address, SalesforceAddressType
from application.models.floor_price import FloorPrice
from utils.models import CustomBaseModelMixin
from utils.salesforce_model_mixin import SalesforceModelMixin, SalesforceObjectType

COMPLETED_LISTING_STATUSES = ["Listed", "Under Contract"]


class CurrentHome(CustomBaseModelMixin, SalesforceModelMixin):
    # Salesforce Fields
    OUTSTANDING_LOAN_AMOUNT_FIELD = 'Outstanding_loan_amount__c'

    LISTING_STATUS_FIELD = "Listing_Status__c"
    LISTING_URL_FIELD = "Listing_URL__c"
    UNDER_CONTRACT_SALES_PRICE_FIELD = "Under_Contract_Sales_Price__c"
    SELLER_CONCESSIONS_FIELD = "Seller_Concessions__c"
    OPTION_PERIOD_EXPIRATION_DATE_FIELD = "Option_Period_Expiration_Date__c"
    CLOSING_DATE_FIELD = "Closing_Date__c"
    REPAIR_OR_UPDATE_DETAIL_FIELD = "Repaire_or_Update_detail__c"
    HAS_BASEMENT_FIELD = "Has_Basement__c"
    BASEMENT_FINISHED_OR_UNFINISHED = "Basement_Finished_or_Unfinished__c"
    BASEMENT_SQ_FT_FIELD = "Basement_Sqft__c"
    DO_YOU_HAVE_A_VIEW_FIELD = "Do_you_have_a_view__c"
    ADDITIONAL_CUSTOMER_NOTES_FIELD = "Additional_Customer_Notes__c"
    NUMBER_OF_STORIES_FIELD = "Number_of_Stories__c"
    BEDROOMS_COUNT_FIELD = "Bedrooms_count__c"
    SQUARE_FOOTAGE_FIELD = "Square_Footage__c"
    MASTER_ON_MAIN_FIELD = "Master_on_main__c"
    FULL_BATH_COUNT_FIELD = "Full_bath_count__c"
    PARTIAL_BATH_COUNT_FIELD = "Partial_bath_count__c"
    KITCHEN_APPLIANCES_TYPE_FIELD = "Kitchen_Appliances_Type__c"
    KITCHEN_FEATURES_FIELD = "Kitchen_features__c"
    COUNTERS_TYPES_FIELD = "Counters_types__c"
    MASTER_BATH_CONDITION_FIELD = "Master_bath_condition__c"
    KITCHEN_REMODEL_FIELD = "Kitchen_remodel__c"
    MASTER_BATH_REMODEL_FIELD = "Master_bath_remodel__c"
    INTERIOR_WALL_CONDITION_FIELD = "Interior_wall_condition__c"
    FLOORING_TYPE_FIELD = "Flooring_Type__c"
    GARAGE_SPACES_COUNT_FIELD = "Garage_spaces_count__c"
    ROOF_AGE_FIELD = "Roof_age__c"
    EXTERIOR_WALLS_TYPE_FIELD = "Exterior_walls_type__c"
    OTHER_HOME_SITUATIONS_FIELD = "Other_home_situations__c"
    HVAC_AGE_FIELD = "Hvac_age__c"
    FLOODZONE_FIELD = "Floodzone__c"
    CUSTOMER_HOME_VALUE_OPINION_FIELD = "Customer_home_value_opinion__c"
    OLD_HOME_CUSTOMER_HOME_VALUE_OPINION_FIELD = "Customer_opinion_of_value__c"
    ADDTIONS_MADE_FIELD = "Addtions_made__c"
    ADDITION_SIZE_FIELD = "addition_size__c"
    ADDITION_TYPE_FIELD = "addition_type__c"
    CARPET_CONDITON_FIELD = "Carpet_conditon__c"
    HARDWOOD_CONDITION_FIELD = "Hardwood_condition__c"
    POOL_FIELD = "Pool__c"
    BACK_YARD_CONDITION_FIELD = "Back_yard_condition__c"
    FRONT_YARD_CONDITION_FIELD = "Front_yard_condition__c"
    SIDES_WITH_MASONARY_FIELD = "Sides_with_masonary__c"
    CUSTOMER_ID = "Customer__c"
    NAME = "Name"
    CURRENT_HOME_MARKET_VALUE_FIELD = 'Market_Value_Valuations__c'

    # Model Fields
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    closing_date = models.DateTimeField(default=None, blank=True, null=True)
    final_sales_price = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    market_value = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    outstanding_loan_amount = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    floor_price = models.ForeignKey(FloorPrice, blank=True, null=True, on_delete=models.CASCADE)
    customer_value_opinion = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    attributes = JSONField(blank=True, null=True)

    listing_status = models.CharField(max_length=50, blank=True, null=True) # Under contract or listed
    listing_url = models.URLField(blank=True, null=True)
    total_concession_amount = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    option_period_expiration_date = models.DateTimeField(blank=True, null=True)
    floors_count = models.IntegerField(blank=True, null=True)
    bedrooms_count = models.IntegerField(blank=True, null=True)
    master_on_main = models.NullBooleanField()
    home_size_sq_ft = models.IntegerField(blank=True, null=True)
    has_made_addition = models.NullBooleanField()
    addition_type = models.CharField(max_length=50, blank=True, null=True) # Permitted or unpermitted
    addition_size_sq_ft = models.IntegerField(blank=True, null=True)
    has_basement = models.NullBooleanField()
    basement_type = models.CharField(max_length=50, blank=True, null=True) # Finished or unfinished
    basement_size_sq_ft = models.IntegerField(blank=True, null=True)
    kitchen_countertop_type = models.CharField(max_length=50, blank=True, null=True)
    kitchen_appliance_type = models.CharField(max_length=50, blank=True, null=True)
    kitchen_features = ArrayField(models.CharField(max_length=50, blank=True, null=True), blank=True, null=True)
    kitchen_has_been_remodeled = models.CharField(max_length=50, blank=True, null=True)
    master_bathroom_condition = models.CharField(max_length=50, blank=True, null=True)
    full_bathrooms_count = models.IntegerField(blank=True, null=True)
    partial_bathrooms_count = models.IntegerField(blank=True, null=True)
    interior_walls_condition = models.CharField(max_length=50, blank=True, null=True)
    flooring_types = ArrayField(models.CharField(max_length=50, blank=True, null=True), blank=True, null=True)
    hardwood_flooring_condition = models.CharField(max_length=50, blank=True, null=True)
    carpet_flooring_condition = models.CharField(max_length=50, blank=True, null=True)
    front_yard_condition = models.CharField(max_length=50, blank=True, null=True)
    back_yard_condition = models.CharField(max_length=50, blank=True, null=True)
    exterior_walls_types = ArrayField(models.CharField(max_length=50, blank=True, null=True), blank=True, null=True)
    sides_with_masonry_count = models.CharField(max_length=50, blank=True, null=True)
    roof_age_range = models.CharField(max_length=50, blank=True, null=True)
    pool_type = models.CharField(max_length=50, blank=True, null=True)
    garage_spaces_count = models.CharField(max_length=20, blank=True, null=True)
    hvac_age_range = models.CharField(max_length=50, blank=True, null=True)
    home_features = ArrayField(models.CharField(max_length=50, blank=True, null=True), blank=True, null=True)
    in_floodzone = models.CharField(max_length=50, blank=True, null=True)
    property_view_type = models.CharField(max_length=50, blank=True, null=True)
    repair_or_update_detail = models.TextField(blank=True, null=True)
    anything_needs_repairs = models.NullBooleanField()
    made_repairs_or_updates = models.NullBooleanField()
    customer_notes = models.TextField(blank=True, null=True)
    under_contract_sales_price = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    salesforce_id = models.CharField(max_length=255, editable=False, blank=True, null=True)

    def salesforce_field_mapping(self):
        return {
            self.LISTING_STATUS_FIELD: self.listing_status,
            self.LISTING_URL_FIELD: self.listing_url,
            self.UNDER_CONTRACT_SALES_PRICE_FIELD: self.under_contract_sales_price,
            self.SELLER_CONCESSIONS_FIELD: self.total_concession_amount,
            self.OPTION_PERIOD_EXPIRATION_DATE_FIELD: self.option_period_expiration_date.date() if self.option_period_expiration_date else None,
            self.CLOSING_DATE_FIELD: self.closing_date.date() if self.closing_date else None,
            self.HAS_BASEMENT_FIELD: self.has_basement,
            self.BASEMENT_FINISHED_OR_UNFINISHED: self.basement_type,
            self.BASEMENT_SQ_FT_FIELD: self.basement_size_sq_ft,
            self.DO_YOU_HAVE_A_VIEW_FIELD: self.property_view_type,
            self.ADDITIONAL_CUSTOMER_NOTES_FIELD: self.customer_notes,
            self.NUMBER_OF_STORIES_FIELD: self.floors_count,\
            self.BEDROOMS_COUNT_FIELD: self.bedrooms_count,
            self.SQUARE_FOOTAGE_FIELD: self.home_size_sq_ft,
            self.MASTER_ON_MAIN_FIELD: self.master_on_main,
            self.FULL_BATH_COUNT_FIELD: self.full_bathrooms_count,
            self.PARTIAL_BATH_COUNT_FIELD: self.partial_bathrooms_count,
            self.KITCHEN_APPLIANCES_TYPE_FIELD: self.kitchen_appliance_type,
            self.KITCHEN_FEATURES_FIELD: self.kitchen_features,
            self.COUNTERS_TYPES_FIELD: self.kitchen_countertop_type,
            self.MASTER_BATH_CONDITION_FIELD: self.master_bathroom_condition,
            self.KITCHEN_REMODEL_FIELD: self.kitchen_has_been_remodeled,
            self.INTERIOR_WALL_CONDITION_FIELD: self.interior_walls_condition,
            self.FLOORING_TYPE_FIELD: self.flooring_types,
            self.GARAGE_SPACES_COUNT_FIELD: self.garage_spaces_count,
            self.ROOF_AGE_FIELD: self.roof_age_range,
            self.EXTERIOR_WALLS_TYPE_FIELD: self.exterior_walls_types,
            self.OTHER_HOME_SITUATIONS_FIELD: self.home_features,
            self.HVAC_AGE_FIELD: self.hvac_age_range,
            self.FLOODZONE_FIELD: self.in_floodzone,
            self.ADDTIONS_MADE_FIELD: self.has_made_addition,
            self.ADDITION_SIZE_FIELD: self.addition_size_sq_ft,
            self.ADDITION_TYPE_FIELD: self.addition_type,
            self.CARPET_CONDITON_FIELD: self.carpet_flooring_condition,
            self.HARDWOOD_CONDITION_FIELD: self.hardwood_flooring_condition,
            self.POOL_FIELD: self.pool_type,
            self.BACK_YARD_CONDITION_FIELD: self.back_yard_condition,
            self.FRONT_YARD_CONDITION_FIELD: self.front_yard_condition,
            self.SIDES_WITH_MASONARY_FIELD: self.sides_with_masonry_count,
            self.REPAIR_OR_UPDATE_DETAIL_FIELD: self.repair_or_update_detail,
            self.OUTSTANDING_LOAN_AMOUNT_FIELD: self.outstanding_loan_amount,
            self.OLD_HOME_CUSTOMER_HOME_VALUE_OPINION_FIELD: self.customer_value_opinion
        }

    def to_salesforce_representation(self, account_sf_id=None):
        payload = super().to_salesforce_representation()
        payload[self.CUSTOMER_ID] = account_sf_id
        payload[self.NAME] = self.address.get_inline_address()
        payload.update(self.address.to_salesforce_representation(SalesforceAddressType.GENERAL_ADDRESS))
        return payload

    def salesforce_object_type(self):
        return SalesforceObjectType.OLD_HOME
