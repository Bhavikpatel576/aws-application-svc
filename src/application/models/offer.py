import logging
from enum import Enum

from django.db import models

from application.models.address import Address
from application.models.application import Application
from application.models.new_home_purchase import NewHomePurchase
from utils.models import CustomBaseModelMixin
from utils.property_data_aggregator import PropertyDataAggregatorClient, PropertyDataAggregatorClientException
from utils.salesforce_model_mixin import SalesforceModelMixin, SalesforceObjectType

logger = logging.getLogger(__name__)


class PropertyType(str, Enum):
    SINGLE_FAMILY = 'Single Family',
    MULTI_FAMILY = 'Multi-Family',
    LUXURY = 'Luxury',
    CONDO = 'Condo',
    LOT = 'Lot'
    OTHER = 'Other'


class ContractType(str, Enum):
    RESALE = 'Resale',
    NEW_BUILD = 'New Build'


class OtherOffers(str, Enum):
    NO = 'No',
    NOT_SURE = 'Not sure'
    UNDER_FIVE = '1-4'
    OVER_OR_EQ_TO_FIVE = '5+'


class PlanToLeaseBackToSeller(str, Enum):
    NO = 'No',
    YES = 'Yes',
    NOT_SURE = 'Not Sure'


class WaiveAppraisal(str, Enum):
    NOT_ELIGIBLE = 'Not eligible'
    YES = 'Yes'
    NO_NOT_COMFORTABLE = 'No - not comfortable covering any delta'
    NO_PARTIAL_DELTA = 'No - only comfortable covering partial delta'
    NO_UNDECIDED = 'No - undecided on covering delta & wants to know value first'
    NO_OTHER = 'No - Other'


class OfferStatus(str, Enum):
    # App-svc uses Incomplete and Complete for deciding when to sync offer to Salesforce. We do not push
    # offer status to salesforce
    INCOMPLETE = 'Incomplete'
    COMPLETE = 'Complete'
    # Salesforce options for offer status
    REQUESTED = 'Requested'
    MOP_COMPLETE = 'MOP Complete'
    APPROVED = 'Approved'
    BACKUP_POSITION_ACCEPTED = 'Backup Position Accepted'
    DENIED = 'Denied'
    WON = 'Won'
    LOST = 'Lost'
    CANCELLED = 'Cancelled'
    CONTRACT_CANCELLED = 'Contract Cancelled'


class Offer(CustomBaseModelMixin, SalesforceModelMixin):
    # Salesforce Fields
    OFFER_SALESFORCE_ID = 'Id'
    OFFER_TRANSACTION_ID = 'Offer__c'
    YEAR_BUILT_FIELD = 'Year_Home_Built__c'
    HOME_SQUARE_FOOTAGE_FIELD = 'Home_Square_Footage__c'
    PROPERTY_TYPE_FIELD = 'New_Home_Property_Type__c'
    LESS_THAN_ONE_ACRE_FIELD = 'New_Home_Less_Than_1_Acre__c'
    HOME_LIST_PRICE_FIELD = 'New_Home_List_Price__c'
    OFFER_PRICE_FIELD = 'New_Home_Offer_Price__c'
    CONTRACT_TYPE_FIELD = 'Contract_Type__c'
    OTHER_OFFER_FIELD = 'Competing_Offers__c'
    OFFER_DEADLINE_FIELD = 'Offer_Deadline_date_time__c'
    LEASE_BACK_TO_SELLER_FIELD = 'Intended_Lease_Back__c'
    WAIVE_APPRAISAL_FIELD = 'Customer_Appraisal_Waiver_Decision__c'
    CUSTOMER_FIELD = 'Customer__c'
    STATUS_FIELD = 'Status__c'
    ADDRESS_STREET_FIELD = 'Homeward_Purchase_Street__c'
    ADDRESS_CITY_FIELD = 'Homeward_Purchase_City__c'
    ADDRESS_STATE_FIELD = 'State__c'
    ADDRESS_ZIP_FIELD = 'Homeward_Purchase_Zip__c'
    ALREADY_UNDER_CONTRACT_FIELD = 'Takeover__c'
    PREFERRED_CLOSING_DATE = 'Close_Date__c'
    HOMEWARD_ID = 'Homeward_ID__c'
    FUNDING_TYPE = 'Funding_Type__c'
    FINANCE_APPROVED_CLOSE_DATE = 'Finance_Approved_Closed_Date__c'

    pda_enrichment_fields = [('office_name', 'office_name')]

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="offers")
    year_built = models.IntegerField(blank=True, null=True)
    home_square_footage = models.IntegerField(blank=True, null=True)
    property_type = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in PropertyType], blank=True, null=True)
    less_than_one_acre = models.BooleanField(blank=True, null=True)
    home_list_price = models.DecimalField(max_digits=11, decimal_places=2, blank=True, null=True)
    offer_price = models.DecimalField(max_digits=11, decimal_places=2, blank=True, null=True)
    contract_type = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in ContractType], blank=True, null=True)
    other_offers = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in OtherOffers], blank=True, null=True)
    offer_deadline = models.DateTimeField(blank=True, null=True)
    plan_to_lease_back_to_seller = models.CharField(max_length=50,
                                                    choices=[(tag.value, tag.value) for tag in PlanToLeaseBackToSeller], blank=True, null=True)
    waive_appraisal = models.CharField(max_length=100, choices=[(tag.value, tag.value) for tag in WaiveAppraisal], blank=True, null=True)
    already_under_contract = models.BooleanField(default=False)
    comments = models.TextField(blank=True, null=True)
    offer_property_address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name="offers", blank=True,
                                               null=True)
    status = models.TextField(default='Incomplete', choices=[(tag.value, tag.value) for tag in OfferStatus])
    salesforce_id = models.TextField(blank=True, null=True, unique=True)
    pda_listing_uuid = models.UUIDField(blank=True, null=True)  # property data aggregator listing model uuid
    mls_listing_id = models.TextField(blank=True, null=True)  # mls id
    bedrooms = models.DecimalField(max_digits=11, decimal_places=2, blank=True, null=True)
    bathrooms = models.DecimalField(max_digits=11, decimal_places=2, blank=True, null=True)
    photo_url = models.TextField(blank=True, null=True)
    preferred_closing_date = models.DateField(blank=True, null=True)
    offer_source = models.TextField(blank=True, null=True)
    hoa = models.BooleanField(null=True, blank=True)
    funding_type = models.TextField(blank=True, null=True)
    finance_approved_close_date = models.DateField(blank=True, null=True)
    office_name = models.TextField(blank=True, null=True)
    new_home_purchase = models.OneToOneField(NewHomePurchase, related_name='offer', on_delete=models.CASCADE, blank=True, null=True)

    def __init__(self, *args, **kwargs):
        self._is_save_from_salesforce = False
        super(Offer, self).__init__(*args, **kwargs)

    @property
    def is_save_from_salesforce(self):
        return self._is_save_from_salesforce

    @is_save_from_salesforce.setter
    def is_save_from_salesforce(self, val):
        self._is_save_from_salesforce = val

    salesforce_object_type = SalesforceObjectType.OFFER
    
    def salesforce_field_mapping(self):
        return {
            self.YEAR_BUILT_FIELD: self.year_built,
            self.HOME_SQUARE_FOOTAGE_FIELD: self.home_square_footage,
            self.PROPERTY_TYPE_FIELD: self.property_type,
            self.LESS_THAN_ONE_ACRE_FIELD: 'Yes' if self.less_than_one_acre else 'No',
            self.HOME_LIST_PRICE_FIELD: self.home_list_price,
            self.OFFER_PRICE_FIELD: self.offer_price,
            self.CONTRACT_TYPE_FIELD: self.contract_type,
            self.OTHER_OFFER_FIELD: self.other_offers,
            self.OFFER_DEADLINE_FIELD: self.offer_deadline.strftime("%Y-%m-%dT%H:%M:%S") if self.offer_deadline else None,
            self.LEASE_BACK_TO_SELLER_FIELD: self.plan_to_lease_back_to_seller,
            self.WAIVE_APPRAISAL_FIELD: self.waive_appraisal,
            self.CUSTOMER_FIELD: self.application.new_salesforce,
            self.ALREADY_UNDER_CONTRACT_FIELD: 'Yes' if self.already_under_contract else 'No',
            self.ADDRESS_STREET_FIELD: self.offer_property_address.street,
            self.ADDRESS_CITY_FIELD: self.offer_property_address.city,
            self.ADDRESS_STATE_FIELD: self.offer_property_address.state,
            self.ADDRESS_ZIP_FIELD: self.offer_property_address.zip,
            self.PREFERRED_CLOSING_DATE: self.preferred_closing_date,
            self.HOMEWARD_ID: self.id,
            self.FUNDING_TYPE: self.funding_type,
            self.FINANCE_APPROVED_CLOSE_DATE: self.finance_approved_close_date.strftime(
                "%Y-%m-%dT%H:%M:%SZ") if self.finance_approved_close_date else None
        }

    def save(self, *args, **kwargs):
        if self.pda_listing_uuid:
            self.attempt_enrich_from_property_data_aggregator()
        else:
            self.clear_pda_listing_info()

        if self.status != 'Incomplete' and not self.is_save_from_salesforce:
            self.attempt_push_to_salesforce()

        super(Offer, self).save(*args, **kwargs)

    def attempt_enrich_from_property_data_aggregator(self):
        old_pda_listing_uuid = Offer.objects.get(id=self.id).pda_listing_uuid if self.created_at else None
        if old_pda_listing_uuid != self.pda_listing_uuid:
            try:
                listing_info = PropertyDataAggregatorClient().get_listing(self.pda_listing_uuid)
                self.mls_listing_id = listing_info.get("listing_id")
                self.year_built = listing_info.get("year_built")
                self.home_square_footage = listing_info.get("square_feet")
                self.photo_url = listing_info.get("photo_url")
                self.bedrooms = listing_info.get("total_bedrooms")
                self.bathrooms = listing_info.get("total_bathrooms")
                self.hoa = listing_info.get("has_hoa")
                for field in self.pda_enrichment_fields:
                    setattr(self, field[0], listing_info.get(field[1]))


                try:
                    acres_num = float(listing_info.get("acres"))
                    self.less_than_one_acre = acres_num < 1
                except (ValueError, TypeError):
                    self.less_than_one_acre = None

                self.home_list_price = listing_info.get("listing_price")

                if self.offer_property_address:
                    self.offer_property_address.street = listing_info.get('display_address')
                    self.offer_property_address.city = listing_info.get('city')
                    self.offer_property_address.state = listing_info.get('state')
                    self.offer_property_address.zip = listing_info.get('postal_code')
                    self.offer_property_address.save()
                else:
                    self.offer_property_address = Address.objects.create(street=listing_info.get('display_address'),
                                                                         city=listing_info.get('city'),
                                                                         state=listing_info.get('state'),
                                                                         zip=listing_info.get('postal_code'))
            except PropertyDataAggregatorClientException:
                pass

    def clear_pda_listing_info(self):
        # skip record if being created or synced from salesforce
        if not self.created_at or self._is_save_from_salesforce:
            return

        old_offer_property = Offer.objects.get(id=self.id).offer_property_address
        # need this check for patching single listing fields where offer property address does not change
        if old_offer_property != self.offer_property_address:
            self.pda_listing_uuid = None
            self.mls_listing_id = None
            self.year_built = None
            self.home_square_footage = None
            self.photo_url = None
            self.bedrooms = None
            self.bathrooms = None
            self.less_than_one_acre = None
            self.home_list_price = None

    def attempt_push_to_salesforce(self):
        from utils.salesforce import homeward_salesforce
        try:
            if self.salesforce_id:
                data = self.to_salesforce_representation()
                data.pop('Customer__c')
                homeward_salesforce.update_salesforce_object(self.salesforce_id,
                                                             data,
                                                             self.salesforce_object_type)
            else:
                salesforce_id = homeward_salesforce.create_new_salesforce_object(self.to_salesforce_representation(),
                                                                                 self.salesforce_object_type)
                self.salesforce_id = salesforce_id
        except Exception as e:
            logger.exception("Failed sending offer to salesforce", exc_info=e, extra=dict(
                type="failed_sending_offer_to_salesforce_in_push",
                offer_id=self.id
            ))
