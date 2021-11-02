import logging
from enum import Enum
from typing import List, Union

from django.conf import settings
from django.contrib.postgres.fields import JSONField, ArrayField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Index

from application import constants
from application.models.address import Address, SalesforceAddressType
from application.models.builder import Builder
from application.models.current_home import CurrentHome
from application.models.customer import Customer
from application.models.floor_price import FloorPriceType
from application.models.internal_support_user import InternalSupportUser
from application.models.mortgage_lender import MortgageLender
from application.models.new_home_purchase import NewHomePurchase
from application.models.preapproval import PreApproval
from application.models.real_estate_agent import AgentType, RealEstateAgent
from application.models.task_category import TaskCategory
from application.models.task_progress import TaskProgress
from application.models.stakeholder_type import StakeholderType
from user.models import User
from utils.models import CustomBaseModelMixin, ModelDiffMixin
from utils.salesforce_model_mixin import (SalesforceModelMixin,
                                          SalesforceObjectType)

# Internal Referral Consts
REAL_ESTATE_AGENT = "real-estate agent"
BUILDER = "home builder"
BROKER = "broker referral"
OPCITY = "opcity"
LOAN_ADVISOR_FAST_TRACK = "loan advisor fast track"
APEX_PARTNER_SITE = "Apex Partner Site"

# Internal Referral Detail Consts
REFERRAL_LINK = "referral link"
REGISTERED_CLIENT = "registered client"
FAST_TRACK_REGISTRATION = "fast track registration"
LOAN_ADVISOR = "loan advisor"

logger = logging.getLogger(__name__)


class HomeBuyingStage(str, Enum):
    RESEARCHING_ONLINE = "researching online"
    VIEWING_LISTINGS = "viewing listings in person"
    MAKING_OFFERS = "making an offer"
    BUILDER = "working with a builder"
    ALREADY_IN_CONTRACT = 'already in contract'


class ApplicationStage(str, Enum):
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    QUALIFIED_APPLICATION = "qualified application"
    FLOOR_PRICE_REQUESTED = "floor price requested"
    FLOOR_PRICE_COMPLETED = "floor price completed"
    APPROVED = "approved"
    DENIED = "denied"
    OFFER_REQUESTED = "offer requested"
    OFFER_SUBMITTED = "offer submitted"
    OPTION_PERIOD = "option period"
    POST_OPTION = "post option"
    HOMEWARD_PURCHASE = "homeward purchase"
    CUSTOMER_CLOSED = "customer closed"
    CANCELLED_CONTRACT = "cancelled contract"
    TRASH = "trash"

    PRE_APPROVAL_STAGES = [QUALIFIED_APPLICATION, FLOOR_PRICE_REQUESTED, FLOOR_PRICE_COMPLETED, INCOMPLETE, COMPLETE]

    APPROVAL_STAGES = [QUALIFIED_APPLICATION, FLOOR_PRICE_REQUESTED, FLOOR_PRICE_COMPLETED, APPROVED]

    POST_APPROVED_STAGES = [APPROVED, DENIED, OFFER_REQUESTED, OFFER_SUBMITTED, OPTION_PERIOD, POST_OPTION,
                            HOMEWARD_PURCHASE, CUSTOMER_CLOSED, CANCELLED_CONTRACT, TRASH]

    @staticmethod
    def from_str(label):
        if label in ('draft', 'incomplete'):
            return ApplicationStage.INCOMPLETE
        elif label in ('complete', 'completed'):
            return ApplicationStage.COMPLETE
        else:
            raise NotImplementedError


class LeadStatus(str, Enum):
    NEW = "New"
    QUALIFYING = "Qualifying"
    NURTURE = "Nurture"
    QUALIFIED = "Qualified"
    ARCHIVE = "Archive"
    TRASH = "Trash"

    @staticmethod
    def from_str(label):
        if label in ('New',):
            return LeadStatus.NEW
        elif label in ('Qualifying',):
            return LeadStatus.QUALIFYING
        elif label in ('Nurture',):
            return LeadStatus.NURTURE
        elif label in ('Archive',):
            return LeadStatus.ARCHIVE
        elif label in ('Trash',):
            return LeadStatus.TRASH
        else:
            raise NotImplementedError


class SelfReportedReferralSource(str, Enum):
    MY_AGENT_QUOTE = "my_agent_quote"
    MY_AGENT = "my_agent"
    MY_LOAN_OFFICER = "my_loan_officer"
    A_FRIEND = "a_friend"
    SOCIAL_MEDIA = 'social_media'
    NEWS_ARTICLE = 'news_article'
    SEARCH_ENGINE = 'search_engine'
    APEX_PARTNER = 'apex_partner'

    # Deprecated (no longer options in UI)
    MY_HOME_BUILDER = "my_home_builder"
    RADIO = "radio"
    SIGN_IN_YARD = "sign_in_yard"


class MortgageStatus(str, Enum):
    VPAL_STARTED = 'VPAL started'
    VPAL_APP_INCOMPLETE = "VPAL App Incomplete"
    VPAL_SUSPENDED = 'VPAL Suspended'
    PREQUALIFIED = 'Pre-Qualified'
    VPAL_APPROVED = 'VPAL approved'
    APP_SUBMITTED = 'App submitted'
    UNDERWRITING = 'Underwriting'
    APPROVED_WITH_CONDITIONS = 'Approved with conditions'
    SUSPENDED = 'Suspended'
    CLEAR_TO_CLOSE = 'Clear to close'
    REQUESTED_CLOSING_DOCS = 'Requested closing docs'
    CLOSING = 'Closing'
    FUNDED = 'Funded'
    WITHDRAWN_INCOMPLETE = 'Withdrawn - Incomplete'
    DENIED = 'Denied'
    VPAL_READY_FOR_REVIEW = 'VPAL Ready For Review'
    VPAL_APPROVED_EXPIRED = 'VPAL Approved - Expired'
    WITHDRAWN_BORROWER_REEQUEST = 'Withdrawn - Borrower request'
    VPAL_DENIED = 'Denied'


class ProductOffering(str, Enum):
    BUY_SELL = 'buy-sell'
    BUY_ONLY = 'buy-only'


class HwMortgageCandidate(str, Enum):
    YES = "Yes - Not Required"
    YES_REQUIRED = "Yes - Required"
    NO = "No"
    NOT_DETERMINED = "Not Determined"

class FloorPriceNotFoundException(Exception):
    pass

class OldHomeApprovedPickList(str, Enum):
    YES = 'Yes'
    NO = 'No'

class Application(CustomBaseModelMixin, SalesforceModelMixin, ModelDiffMixin):
    
    class FilterStatus(str, Enum):
        ARCHIVED = 'Archived'
    
    # Salesforce bi-directional sync Fields
    CUSTOMER_ID_FIELD = 'Customer_Id__c'
    RECORD_TYPE_ID_FIELD = 'RecordTypeId'
    RECORD_TYPE_ID_VALUE = '0124P000000OCbHQAW'

    MIN_PRICE_FIELD = 'Min_Price__c'
    MAX_PRICE_FIELD = 'Max_Price__c'

    APP_LINK_FIELD = 'Homeward_App_Link__c'

    WORKING_WITH_A_LENDER_FIELD = 'Are_you_already_working_with_a_lender__c'

    HOME_TO_SELL_FIELD = 'Do_you_have_a_home_to_sell__c'

    SELF_REPORTED_REFERRAL_SOURCE_FIELD = 'Self_Reported_Referral_Source__c'
    SELF_REPORTED_REFERRAL_SOURCE_DETAIL_FIELD = 'Self_Reported_Referral_Source_Detail__c'
    LEAD_SOURCE_FIELD = 'Lead_Source_Text__c'
    LEAD_SOURCE_DETAIL_FIELD = 'Lead_Source_Detail__c'
    LEAD_SOURCE_DETAIL_TWO_FIELD = 'Lead_Source_Detail_2__c'
    INTERNAL_REFERRAL_FIELD = 'Internal_Referral__c'
    INTERNAL_REFERRAL_DETAIL_FIELD = "Internal_Referral_Detail__c"

    TARGET_MOVE_DATE_FIELD = 'Target_move_in_date__c'
    MOVE_BY_DATE_FIELD = 'Move_by_date__c'
    CUSTOMER_REPORTED_STAGE_FIELD = 'Customer_reported_stage__c'
    APPLICATION_STAGE_FIELD = 'Application_Stage__c'

    WORKING_WITH_AN_AGENT_FIELD = 'Are_you_working_with_a_real_estate_agent__c'

    NEEDS_BUYING_AGENT_FIELD = 'Needs_Buying_Agent__c'
    NEEDS_LISTING_AGENT_FIELD = 'Needs_Listing_Agent__c'

    AGENT_PRICING_SHEET_URL_FIELD = 'Agent_Pricing_Sheet__c'
    PRE_ACCOUNT_RESUME_LINK_URL_FIELD = 'Pre_Account_Resume_Link__c'
    AGENT_APP_NOTES_FIELD = 'Agent_App_Notes__c'
    PRODUCT_OFFERING_FIELD: str = 'Product_Offering__c'

    AGENT_CLIENT_CONTACT_PREFERENCE = 'Agent_Client_Contact_Preference__c'

    # One way sync SF fields
    LEAD_STATUS_FIELD = 'Lead_Status__c'
    REASON_FOR_TRASH_FIELD = 'Reason_for_Trash__c'
    BLEND_STATUS_FIELD = 'Blend_Status__c'
    HOMEWARD_MORTGAGE_STATUS_FIELD = 'HW_Mortgage_Status__c'
    OWNER_EMAIL_FIELD = 'Owner_Email__c'
    # TODO Remove after transition (CLOS-222)
    REASSIGNED_CONTRACT_FIELD: str = 'ReassignedContract__c'
    HW_MORTGAGE_CANDIDATE = 'HW_Mortgage_Candidate__c'
    BUY_AGENT_TRANSACTION_COORDINATOR_EMAIL = 'Agent_s_TC_Email__c'
    NEW_SERVICE_AGREEMENT_ACKNOWLEDGED_DATE = 'Newest_Service_Agreement_Acknowledge_DT__c'
    SALESFORCE_COMPANY_ID_FIELD = 'Apex_Referral_Partner__c'
    APPROVAL_SPECIALIST = 'Approval_Specialist__c'

    # SF Fields used for creating test data
    ESTIMATED_DOWN_PAYMENT = 'Estimated_Down_Payment__c'
    LENDER_PRE_APPROVAL_AMOUNT = 'Lender_Pre_Approval_Amount__c'
    ADJUSTED_AVM = 'Adjusted_AVM_field__c'
    FLOOR_PRICE = 'Prelim_Floor_Price__c'
    OLD_HOME_APPROVED_PURCHASE_PRICE = 'Old_Home_approved_for_purchase__c'
    CX_ASSIGNED = 'CX_Assigned__c'

    estimated_down_payment = None
    lender_pre_approval_amount = None
    adjusted_avm = None
    floor_price = None
    old_home_approved_purchase_price: OldHomeApprovedPickList = None
    cx_assigned = None

    # Model Fields
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    current_home = models.ForeignKey(CurrentHome, on_delete=models.SET_NULL, null=True, related_name="application")
    shopping_location = models.CharField(max_length=255)  # this field is deprecated an slated for removal
    home_buying_location = models.ForeignKey(Address, on_delete=models.SET_NULL, blank=True, null=True,
                                             related_name='home_buying_location')
    home_buying_stage = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in HomeBuyingStage])
    stage = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in ApplicationStage])
    lead_status = models.CharField(max_length=50, choices=[(tag.value, tag.value) for tag in LeadStatus],
                                   default=LeadStatus.NEW)
    min_price = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    max_price = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    move_in = models.CharField(max_length=255, blank=True, null=True)
    move_by_date = models.DateField(null=True, blank=True)
    start_date = models.DateTimeField(auto_now_add=True)
    mortgage_lender = models.ForeignKey(MortgageLender, on_delete=models.SET_NULL, blank=True, null=True)
    # todo: delete real_estate_agent after migrating
    real_estate_agent = models.ForeignKey(RealEstateAgent, on_delete=models.SET_NULL, blank=True, null=True)
    listing_agent = models.ForeignKey(RealEstateAgent, on_delete=models.SET_NULL, blank=True, null=True,
                                      related_name='listing_agent')
    buying_agent = models.ForeignKey(RealEstateAgent, on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name='buying_agent')

    builder = models.ForeignKey(Builder, on_delete=models.SET_NULL, blank=True, null=True)
    offer_property_address = models.ForeignKey(Address, on_delete=models.SET_NULL, blank=True, null=True,
                                               related_name='offer_property_address')
    pushed_to_hubspot_on = models.DateTimeField(default=None, blank=True, null=True, )
    hubspot_context = JSONField(null=True, blank=True)
    pushed_to_salesforce_on = models.DateTimeField(default=None, blank=True, null=True, )
    new_salesforce = models.CharField(max_length=255, editable=False, blank=True, null=True)
    utm = JSONField(blank=True, null=True, default=dict)
    lead_source = models.CharField(max_length=255, blank=True, null=True)
    lead_source_drill_down_1 = models.CharField(max_length=255, blank=True, null=True)
    lead_source_drill_down_2 = models.CharField(max_length=255, blank=True, null=True)
    self_reported_referral_source = models.CharField(max_length=255, blank=True, null=True)
    self_reported_referral_source_detail = models.CharField(max_length=255, blank=True, null=True)
    reason_for_trash = models.CharField(max_length=255, blank=True, null=True)
    internal_referral = models.CharField(max_length=255, blank=True, null=True)
    needs_listing_agent = models.BooleanField(blank=True, null=True)
    needs_buying_agent = models.BooleanField(blank=True, null=True)
    has_consented_to_receive_electronic_documents = models.BooleanField(default=False)
    needs_lender = models.BooleanField(blank=True, null=True)
    blend_status = models.CharField(max_length=50, blank=True, null=True)
    internal_referral_detail = models.CharField(max_length=255, blank=True, null=True)
    questionnaire_response_id = models.CharField(max_length=255, blank=True, null=True)
    mortgage_status = models.CharField(max_length=50, blank=True, null=True)
    homeward_owner_email = models.EmailField(blank=True, null=True)
    preapproval = models.OneToOneField(PreApproval, on_delete=models.CASCADE, blank=True, null=True)
    new_home_purchase = models.OneToOneField(NewHomePurchase, on_delete=models.CASCADE, blank=True, null=True)
    agent_notes = models.TextField(blank=True, null=True)
    cx_manager = models.ForeignKey(InternalSupportUser, on_delete=models.PROTECT, related_name="cx_manager", blank=True,
                                   null=True)
    loan_advisor = models.ForeignKey(InternalSupportUser, on_delete=models.PROTECT, related_name="loan_advisor",
                                     blank=True, null=True)
    product_offering = models.TextField()
    agent_client_contact_preference = models.TextField(blank=True, null=True)
    hw_mortgage_candidate = models.CharField(max_length=50,
                                             choices=[(tag.value, tag.value) for tag in HwMortgageCandidate],
                                             default=HwMortgageCandidate.NOT_DETERMINED)
    apex_partner_slug = models.TextField(blank=True, null=True)
    salesforce_company_id = models.TextField(blank=True, null=True)
    approval_specialist = models.ForeignKey(InternalSupportUser, on_delete=models.PROTECT,
                                            related_name="approval_specialist", blank=True, null=True)
    filter_status = ArrayField(models.CharField(max_length=10, choices=[('Archived', 'Archived')], blank=True, null=True), default=list)
    agent_service_buying_agent_id = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            Index(fields=['new_salesforce'])
        ]

    @property
    def new_service_agreement_acknowledged_date(self):
        try:
            acknowledgments = self.acknowledgements.filter(disclosure__name__in=[constants.SERVICE_AGREEMENT_TX,
                                                                                 constants.SERVICE_AGREEMENT_TX_BUY_ONLY,
                                                                                 constants.SERVICE_AGREEMENT_TX_RA,
                                                                                 constants.SERVICE_AGREEMENT_TX_RA_BUY_ONLY,
                                                                                 constants.SERVICE_AGREEMENT_CO,
                                                                                 constants.SERVICE_AGREEMENT_CO_BUY_ONLY,
                                                                                 constants.SERVICE_AGREEMENT_GA,
                                                                                 constants.SERVICE_AGREEMENT_GA_BUY_ONLY,
                                                                                 constants.SERVICE_AGREEMENT_AZ,
                                                                                 constants.SERVICE_AGREEMENT_AZ_BUY_ONLY])
            if acknowledgments:
                return acknowledgments.order_by('-updated_at').first().acknowledged_at
        except Exception as e:
            logger.exception("exception thrown trying to determine new SA acknowledgement dat", exc_info=e, extra=dict(
                type='new_service_agreement_error'))
            return None

    def get_link(self) -> str:
        """
        Get CRM frontend Link.
        """
        if settings.FRONTEND_APPLICATION_OVERVIEW_URL:
            return settings.FRONTEND_APPLICATION_OVERVIEW_URL.format(self.pk)
        else:
            raise Exception("Environment variable FRONTEND_APPLICATION_OVERVIEW_URL not set")

    def is_buy_sell(self):
        return self.product_offering == ProductOffering.BUY_SELL

    def get_current_home_state(self):
        if self.current_home and self.current_home.address:
            return self.current_home.address.state
        return None

    def get_purchasing_state(self):
        address = self.get_purchasing_address()
        if address:
            return address.state
        return None

    def get_buying_agent_brokerage_name(self):
        if self.buying_agent is not None and self.buying_agent.brokerage is not None:
            return self.buying_agent.brokerage.name

    def get_purchasing_address(self):
        if self.offer_property_address:
            return self.offer_property_address

        if self.home_buying_location:
            return self.home_buying_location
        return None

    def has_disclosures(self):
        return self.acknowledgements.filter(disclosure__active=True).count() > 0

    def is_agent_registered_client(self) -> bool:
        return (self.internal_referral == REAL_ESTATE_AGENT or
                self.internal_referral == OPCITY or
                self.internal_referral == BROKER) and self.internal_referral_detail == REGISTERED_CLIENT

    def user_exists_for_application(self) -> bool:
        return User.objects.filter(email=self.customer.email).exists()

    def get_cta_link(self):
        if self.is_agent_registered_client() and not self.user_exists_for_application():
            return self.get_pricing_url()
        else:
            return self.build_resume_link()

    def get_resume_path(self):
        resume_path = "resume/"
        if self.questionnaire_response_id:
            resume_path = resume_path + self.questionnaire_response_id
        else:
            logger.warning("Could not build resume link because questionnaire_response_id "
                           "was not populated", extra=dict(type='unable_to_build_resusme_path', application_id=self.pk))
        return resume_path

    def build_resume_link(self):
        return settings.ONBOARDING_BASE_URL + self.get_resume_path()

    def build_apex_resume_link(self):
        resume_path = self.get_resume_path()
        if self.apex_partner_slug:
            return "{}{}/{}".format(settings.APEX_ONBOARDING_BASE_URL, self.apex_partner_slug, resume_path)
        else:
            return self.build_resume_link()

    def are_all_tasks_complete(self) -> bool:
        return all([status.status == TaskProgress.COMPLETED for status in self.task_statuses
                   .exclude(task_obj__category=TaskCategory.HOMEWARD_MORTGAGE).all()])

    def get_buying_agent_email(self) -> str:
        if self.buying_agent is not None and self.buying_agent.email is not None:
            return self.buying_agent.email

    def get_buying_agent_name(self):
        if self.buying_agent is not None and self.buying_agent.name is not None:
            return self.buying_agent.name

    def get_cx_email(self) -> str:
        if self.cx_manager is not None and self.cx_manager.email is not None:
            return self.cx_manager.email

    def get_loan_advisor_email(self) -> str:
        if self.loan_advisor is not None:
            return self.loan_advisor.email
    
    def get_loan_advisor_first_name(self) -> str:
        if self.loan_advisor is not None:
            return self.loan_advisor.first_name
    
    def get_loan_advisor_last_name(self) -> str:
        if self.loan_advisor is not None:
            return self.loan_advisor.last_name

    def get_transaction_coordinator_email(self) -> str:
        tc = self.stakeholders.filter(type=StakeholderType.TRANSACTION_COORDINATOR).first()
        if tc:
            return tc.email

    def get_approval_specialist_email(self) -> str:
        if self.approval_specialist is not None and self.approval_specialist.email is not None:
            return self.approval_specialist.email
        else:
            return "hello@homewardmortgage.com"

    def get_approval_specialist_first_name(self) -> str:
        if self.approval_specialist is not None and self.approval_specialist.first_name is not None:
            return self.approval_specialist.first_name
        else:
            return "Homeward"

    def get_approval_specialist_last_name(self) -> str:
        if self.approval_specialist is not None and self.approval_specialist.last_name is not None:
            return self.approval_specialist.last_name
        else:
            return "Mortgage"

    def generate_cc_emails_list(self) -> List[str]:
        cc_email_list = []
        agent_email = self.get_buying_agent_email()
        if agent_email:
            cc_email_list.append(agent_email)
        if self.customer.co_borrower_email:
            cc_email_list.append(self.customer.co_borrower_email)
        cx_email = self.get_cx_email()
        if cx_email:
            cc_email_list.append(cx_email)
        tc_email = self.get_transaction_coordinator_email()
        if tc_email:
            cc_email_list.append(tc_email)
        return cc_email_list

    def get_formatted_floor_price(self) -> str:
        if self.current_home is not None \
                and self.current_home.floor_price is not None:
            if self.current_home.floor_price.type == FloorPriceType.REQUIRED:
                if self.current_home.floor_price.amount is not None:
                    return f"${round(self.current_home.floor_price.amount):,}"
                elif self.current_home.floor_price.preliminary_amount is not None:
                    return f"${round(self.current_home.floor_price.preliminary_amount):,} (estimated)"
                else:
                    raise FloorPriceNotFoundException(
                        "something weird happened trying to format floor price for app {}".format(self.id))
        return "Your Homeward transaction does not include a floor price"

    def get_pricing_url(self) -> Union[str, None]:
        try:
            if self.pricing:
                return f'{settings.ONBOARDING_BASE_URL}estimates/view/{self.questionnaire_response_id}'
            else:
                logger.error("Could not build get pricing url because application has no pricing object ",
                             extra=dict(type='unable_to_get_pricing_url', application_id=self.pk))
                return None
        except ObjectDoesNotExist:
            return None

    def get_user(self):
        if self.customer is not None \
                and self.customer.email is not None:
            try:
                return User.objects.get(email=self.customer.email)
            except User.DoesNotExist:
                return None
        else:
            return None

    def salesforce_field_mapping(self):
        return {
            self.CUSTOMER_ID_FIELD: str(self.customer.id),
            self.APPLICATION_STAGE_FIELD: self.stage,
            self.LEAD_SOURCE_FIELD: self.lead_source,
            self.LEAD_SOURCE_DETAIL_FIELD: self.lead_source_drill_down_1,
            self.LEAD_SOURCE_DETAIL_TWO_FIELD: self.lead_source_drill_down_2,
            self.CUSTOMER_REPORTED_STAGE_FIELD: self.home_buying_stage,
            self.TARGET_MOVE_DATE_FIELD: self.move_in,
            self.INTERNAL_REFERRAL_FIELD: self.internal_referral,
            self.INTERNAL_REFERRAL_DETAIL_FIELD: self.internal_referral_detail,
            self.SELF_REPORTED_REFERRAL_SOURCE_FIELD: self.self_reported_referral_source,
            self.SELF_REPORTED_REFERRAL_SOURCE_DETAIL_FIELD: self.self_reported_referral_source_detail,
            self.MIN_PRICE_FIELD: self.min_price,
            self.MAX_PRICE_FIELD: self.max_price,
            self.AGENT_APP_NOTES_FIELD: self.agent_notes,
            self.MOVE_BY_DATE_FIELD: self.move_by_date,
            self.RECORD_TYPE_ID_FIELD: self.RECORD_TYPE_ID_VALUE,
            self.WORKING_WITH_AN_AGENT_FIELD: 'yes' if self.real_estate_agent else 'no',
            self.HOME_TO_SELL_FIELD: 'yes' if self.current_home else 'no',
            self.APP_LINK_FIELD: self.get_link(),
            self.WORKING_WITH_A_LENDER_FIELD: 'yes' if self.mortgage_lender else 'no',
            self.AGENT_PRICING_SHEET_URL_FIELD: self.get_pricing_url(),
            self.PRE_ACCOUNT_RESUME_LINK_URL_FIELD: self.build_resume_link(),
            self.PRODUCT_OFFERING_FIELD: self.product_offering,
            self.NEEDS_BUYING_AGENT_FIELD: self.needs_buying_agent,
            self.NEEDS_LISTING_AGENT_FIELD: self.needs_listing_agent,
            self.AGENT_CLIENT_CONTACT_PREFERENCE: self.agent_client_contact_preference,
            self.NEW_SERVICE_AGREEMENT_ACKNOWLEDGED_DATE: self.new_service_agreement_acknowledged_date.strftime(
                "%Y-%m-%dT%H:%M:%SZ") if self.new_service_agreement_acknowledged_date else None,
            self.SALESFORCE_COMPANY_ID_FIELD: self.salesforce_company_id,
            self.ESTIMATED_DOWN_PAYMENT: self.estimated_down_payment,
            self.LENDER_PRE_APPROVAL_AMOUNT: self.lender_pre_approval_amount,
            self.ADJUSTED_AVM: self.adjusted_avm,
            self.FLOOR_PRICE: self.floor_price,
            self.OLD_HOME_APPROVED_PURCHASE_PRICE: self.old_home_approved_purchase_price,
            self.LEAD_STATUS_FIELD: self.lead_status,
            self.CX_ASSIGNED: self.cx_assigned,
        }

    def to_salesforce_representation(self):
        payload = super().to_salesforce_representation()
        payload.update(self.customer.to_salesforce_representation())
        if self.get_user():
            payload.update(self.get_user().to_salesforce_representation())
        if self.listing_agent:
            payload.update(self.listing_agent.to_salesforce_representation(AgentType.LISTING))
        if self.buying_agent:
            payload.update(self.buying_agent.to_salesforce_representation(AgentType.BUYING))
        if self.mortgage_lender:
            payload.update(self.mortgage_lender.to_salesforce_representation())
        # The Billing Address fields for a salesforce record are currently used to store the current home address
        if self.current_home:
            payload.update(
                self.current_home.address.to_salesforce_representation(SalesforceAddressType.BILLING_ADDRESS))

        if self.home_buying_location:
            payload.update(
                self.home_buying_location.to_salesforce_representation(SalesforceAddressType.BUYING_LOCATION))

        if self.offer_property_address:
            payload.update(
                self.offer_property_address.to_salesforce_representation(SalesforceAddressType.OFFER_ADDRESS))
        return payload

    def salesforce_object_type(self):
        return SalesforceObjectType.ACCOUNT

    def is_hw_mortgage_candidate(self):
        return self.hw_mortgage_candidate == "Yes - Required" or self.hw_mortgage_candidate == "Yes"
