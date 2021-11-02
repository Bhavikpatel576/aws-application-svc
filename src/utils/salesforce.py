import logging
from datetime import datetime
from enum import Enum
from typing import Optional

import pytz
from simple_salesforce import Salesforce as sf, SalesforceExpiredSession
from simple_salesforce.exceptions import (SalesforceGeneralError,
                                          SalesforceMalformedRequest)

from application import constants
from application.models.address import Address
from application.models.application import Application
from application.models.brokerage import Brokerage
from application.models.builder import Builder
from application.models.current_home import CurrentHome
from application.models.customer import Customer
from application.models.floor_price import FloorPrice
from application.models.internal_support_user import InternalSupportUser
from application.models.loan import Loan
from application.models.mortgage_lender import MortgageLender
from application.models.new_home_purchase import NewHomePurchase
from application.models.offer import Offer
from application.models.preapproval import PreApproval
from application.models.real_estate_agent import RealEstateAgent
from application.models.rent import Rent
from application.models.stakeholder import Stakeholder
from application.models.stakeholder_type import StakeholderType
from application.task_operations import run_task_operations
from core import settings
from utils.celery import app as celery_app

logger = logging.getLogger(__name__)

class SalesforceObjectType(str, Enum):
    ACCOUNT = "Account"
    OLD_HOME = "Old_Home__c"
    QUOTE = "Quote__c"
    TRANSACTION = 'Offer__c'

class TranasctionRecordType(str, Enum):
    OLD_HOME_SALE = "Old Home Sale"
    OFFER = "Offer"
    HOMEWARD_PURCHASE = "Homeward Purchase"
    CUSTOMER_PURCHASE = "Customer Purchase"

class SalesforceException(Exception):
    pass


class Salesforce(object):
    SUPPRESSED_SALESFORCE_ERRORS = [
        'UNABLE_TO_LOCK_ROW',  # we should handle this by retry (CF-3609)
        'INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY',  # this is caused by the agent in app-svc having a different
        # sf id than in salesforce, due to the record being merged in
        # SF but not app-svc. fixed by adopting agent service
    ]

    def __init__(self):
        self.salesforce = sf(**settings.NEW_SALESFORCE)

        if self.salesforce is None:
            raise Exception("salesforce was not configured properly")

    def login(self):
        self.salesforce = sf(**settings.NEW_SALESFORCE)

    def get_salesforce(self):
        try:
            self.salesforce.limits()
        except SalesforceExpiredSession:
            self.login()
        return self.salesforce

    def build_sf_url(self, sf_id):
        instance_url = self.salesforce.sf_instance
        return "https://{}/lightning/r/Account/{}/view".format(instance_url, sf_id)

    def get_id_by_email(self, email: str) -> Optional:
        search_query = ("SELECT Id "
                        "FROM Account "
                        "WHERE PersonEmail = '{}' "
                        "and RecordTypeId = '{}'"
                        .format(email, Application.RECORD_TYPE_ID_VALUE))
        results = self.query(search_query)

        if results['totalSize'] == 0:
            return None
        elif results['totalSize'] > 1:
            raise SalesforceException("Found more than one application for email {}".format(email))
        else:
            return results['records'][0]['Id']

    def get_current_home_id_by_account_id(self, account_id: str) -> Optional:
        if not account_id:
            return None
        search_query = ("SELECT Id "
                        "FROM Old_Home__c "
                        "WHERE Customer__c = '{}' "
                        .format(account_id))
        results = self.query(search_query)

        if results['totalSize'] == 0:
            return None
        elif results['totalSize'] > 1:
            raise SalesforceException("Found more than one current home for application {}".format(account_id))
        else:
            return results['records'][0]['Id']
        return None

    def query(self, query):
        return self.get_salesforce().query(query)

    def update_salesforce_object(self, sf_id, data, object_type: SalesforceObjectType):
        sf_model = getattr(self.get_salesforce(), object_type.value)
        try:
            sf_model.update(sf_id, data)
        except SalesforceMalformedRequest as e:
            raise SalesforceException(e)
        except SalesforceGeneralError as e:
            if isinstance(e.content, list) and e.content[0] is not None \
                    and isinstance(e.content[0], dict) and e.content[0].get('errorCode') is not None \
                    and e.content[0].get('errorCode') in self.SUPPRESSED_SALESFORCE_ERRORS:
                logger.exception("Error while syncing to salesforce", exc_info=e, extra=dict(
                    type="error_while_syncing_to_salesforce",
                    sf_id=sf_id,
                    data=data,
                    object_type=object_type,
                    sf_model=sf_model
                ))
            else:
                raise e

    def create_new_salesforce_object(self, data, object_type: SalesforceObjectType):
        sf_model = getattr(self.get_salesforce(), object_type.value)
        try:
            item = sf_model.create(data)
        except SalesforceMalformedRequest as e:
            raise SalesforceException(e)
        return item['id']

    def get_account_by_id(self, sf_id: str):
        return self.get_salesforce().Account.get(sf_id)

    def get_user_by_id(self, sf_id: str):
        return self.get_salesforce().User.get(sf_id)


homeward_salesforce = Salesforce()


def map_if_field_is_present(application_field, person_data, salesforce_field_to_map_to,
                            transform_function=lambda arg: arg):
    if application_field:
        person_data.update({salesforce_field_to_map_to: transform_function(application_field)})


@celery_app.task(queue='application-service-tasks')
def sync_loan_record_from_salesforce(salesforce_data):
    logger.info("Salesforce Payload for sync_loan_record_from_salesforce", extra=dict(
        type="sync_loan_record_from_salesforce",
        data=salesforce_data))

    if Loan.CUSTOMER_FIELD not in salesforce_data:
        raise KeyError('Customer field not provided in Loan SF sync')
    elif salesforce_data.get(Loan.CUSTOMER_FIELD) is None:
        raise ValueError('Customer field cannot be None')
    application = Application.objects.get(new_salesforce=salesforce_data.get(Loan.CUSTOMER_FIELD))
    update_or_create_loan_from_salesforce(application, salesforce_data)


def update_approval_specialist_on_application(application, salesforce_data):
    sf_approval_specialist_id = salesforce_data.get(Application.APPROVAL_SPECIALIST)

    if sf_approval_specialist_id is not None:
        sf_internal_support_user = homeward_salesforce.get_user_by_id(sf_approval_specialist_id)

        if sf_internal_support_user:
            try:
                approval_specialist, created = \
                    update_or_create_internal_support_user_from_salesforce(sf_internal_support_user)
            except (InternalSupportUser.DoesNotExist, InternalSupportUser.MultipleObjectsReturned) as e:
                logger.exception(
                    f"Error getting Support User for ID : {sf_approval_specialist_id}", exc_info=e, extra=dict(
                        type="error_getting_internal_support_user_for_id_from_salesforce",
                        application=application,
                        sf_approval_specialist_id=sf_approval_specialist_id,
                        salesforce_data=salesforce_data
                    ))
            else:
                application.approval_specialist = approval_specialist
                application.save()
                logger.info("Saving approval_specialist to application", extra=dict(
                    type="saving_approval_specialist_to_app_from_salesforce",
                    application_id=application.id,
                    created_internal_support_user=created,
                    sf_approval_specialist_id=sf_approval_specialist_id,
                    approval_specialist_id=approval_specialist.id
                ))


def update_or_create_loan_from_salesforce(application: Application, salesforce_data: dict):
    defaults = {
        'application': application,
        'status': salesforce_data.get(Loan.LOAN_STATUS_FIELD),
        'salesforce_id': salesforce_data.get(Loan.SALESFORCE_ID_FIELD),
        'denial_reason': salesforce_data.get(Loan.DENIAL_REASON_FIELD),
        'base_convenience_fee': salesforce_data.get(Loan.BASE_CONVENIENCE_FEE_FIELD),
        'estimated_broker_convenience_fee_credit':
            salesforce_data.get(Loan.ESTIMATED_BROKER_CONVENIENCE_FEE_CREDIT_FIELD),
        'estimated_mortgage_convenience_fee_credit':
            salesforce_data.get(Loan.ESTIMATED_MORTGAGE_CONVENIENCE_FEE_CREDIT_FIELD),
        'estimated_daily_rent': salesforce_data.get(Loan.ESTIMATED_DAILY_RENT),
        'estimated_monthly_rent': salesforce_data.get(Loan.ESTIMATED_MONTHLY_RENT),
        'estimated_earnest_deposit_percentage': salesforce_data.get(Loan.ESTIMATED_EARNEST_DEPOSIT_PERCENTAGE)
    }
    blend_application_id = salesforce_data.get(Loan.BLEND_APPLICATION_ID_FIELD)
    return Loan.objects.update_or_create(blend_application_id=blend_application_id, defaults=defaults)


@celery_app.task(queue='application-service-tasks')
def sync_transaction_record_from_salesforce(salesforce_data):
    logger.info("Salesforce payload for sync_transaction_record_from_salesforce", extra=dict(
        type="salesforce_payload_sync_transaction_record_from_salesforce",
        data=salesforce_data
    ))

    if Offer.OFFER_SALESFORCE_ID not in salesforce_data:
        raise KeyError('Transaction ID field not provided in Transaction SF sync')
    elif Offer.OFFER_TRANSACTION_ID not in salesforce_data:
        raise KeyError('Related Offer ID to the Transaction field not provided in Transaction SF sync')
    elif salesforce_data.get(Offer.OFFER_SALESFORCE_ID) is None\
            and salesforce_data.get(Offer.OFFER_TRANSACTION_ID) is None:
        raise ValueError('Both offer ID fields cannot be None')

    record_type = salesforce_data.get(NewHomePurchase.TRANSACTION_RECORD_TYPE)

    if record_type == constants.OFFER_TRANSACTION:
        sync_offer_record_from_salesforce(salesforce_data)
    elif record_type == constants.HOMEWARD_PURCHASE_TRANSACTION:
        sync_homeward_purchase_transaction_record_from_salesforce(salesforce_data)
    elif record_type == constants.CUSTOMER_PURCHASE_TRANSACTION:
        sync_customer_purchase_transaction_record_from_salesforce(salesforce_data)
    elif record_type == constants.OLD_HOME_SALE_TRANSACTION:
        # not synced at the moment
        pass
    else:
        logger.exception(f"Transaction record type is invalid {salesforce_data.get(NewHomePurchase.TRANSACTION_RECORD_TYPE)}",
                         extra=dict(
                             type="invalid_record_type_when_syncing_transaction_from_salesforce",
                             data=salesforce_data,
                             offer_id=salesforce_data.get(Offer.OFFER_TRANSACTION_ID),
                             record_type=salesforce_data.get(NewHomePurchase.TRANSACTION_RECORD_TYPE)
                         ))


@celery_app.task(queue='application-service-tasks')
def sync_offer_record_from_salesforce(salesforce_data):
    logger.info("Salesforce payload for sync_offer_record_from_salesforce", extra=dict(
        type="salesforce_payload_sync_offer_record_from_salesforce",
        data=salesforce_data
    ))

    if salesforce_data.get(Offer.OFFER_SALESFORCE_ID):
        try:
            application = Application.objects.get(new_salesforce=salesforce_data.get(Offer.CUSTOMER_FIELD))
        except Application.DoesNotExist as e:
            logger.exception(f"Couldn't find application when syncing offer {salesforce_data.get(Offer.OFFER_SALESFORCE_ID)}", exc_info=e,
                             extra=dict(
                                 type="no_application_when_syncing_offer_from_salesforce",
                                 data=salesforce_data,
                                 salesforce_id=salesforce_data.get(Offer.OFFER_SALESFORCE_ID)
                             ))
            raise SalesforceException('unable to sync offer due to missing application')

        if salesforce_data.get(Offer.FINANCE_APPROVED_CLOSE_DATE):
            finance_approved_close_date = datetime.strptime(salesforce_data.get(Offer.FINANCE_APPROVED_CLOSE_DATE),
                                                            "%Y-%m-%d").date()
        else:
            finance_approved_close_date = None

        offer_defaults = {
            'application': application,
            'status': salesforce_data.get(Offer.STATUS_FIELD),
            'offer_price': salesforce_data.get(Offer.OFFER_PRICE_FIELD),
            'contract_type': salesforce_data.get(Offer.CONTRACT_TYPE_FIELD),
            'other_offers': salesforce_data.get(Offer.OTHER_OFFER_FIELD),
            'offer_deadline': salesforce_data.get(Offer.OFFER_DEADLINE_FIELD),
            'plan_to_lease_back_to_seller': salesforce_data.get(Offer.LEASE_BACK_TO_SELLER_FIELD),
            'waive_appraisal': salesforce_data.get(Offer.WAIVE_APPRAISAL_FIELD),
            'year_built': salesforce_data.get(Offer.YEAR_BUILT_FIELD),
            'home_square_footage': salesforce_data.get(Offer.HOME_SQUARE_FOOTAGE_FIELD),
            'property_type': salesforce_data.get(Offer.PROPERTY_TYPE_FIELD),
            'less_than_one_acre': salesforce_data.get(Offer.LESS_THAN_ONE_ACRE_FIELD) == 'Yes',
            'home_list_price': salesforce_data.get(Offer.HOME_LIST_PRICE_FIELD),
            'already_under_contract': salesforce_data.get(Offer.ALREADY_UNDER_CONTRACT_FIELD) == 'Yes',
            'funding_type': salesforce_data.get(Offer.FUNDING_TYPE),
            'finance_approved_close_date': finance_approved_close_date,
            'is_save_from_salesforce': True,
            'salesforce_id': salesforce_data.get(Offer.OFFER_SALESFORCE_ID)
        }

        address_defaults = {
            'street': salesforce_data.get(Offer.ADDRESS_STREET_FIELD),
            'city': salesforce_data.get(Offer.ADDRESS_CITY_FIELD),
            'state': salesforce_data.get(Offer.ADDRESS_STATE_FIELD),
            'zip': salesforce_data.get(Offer.ADDRESS_ZIP_FIELD),
        }

        offer, created = Offer.objects.update_or_create(id=salesforce_data.get(Offer.HOMEWARD_ID),
                                                        defaults=offer_defaults)

        if created:
            homeward_salesforce.update_salesforce_object(offer.salesforce_id, {Offer.HOMEWARD_ID: str(offer.id)},
                                                         Offer.salesforce_object_type)

        if offer.offer_property_address:
            Address.objects.filter(id=offer.offer_property_address.id).update(**address_defaults)
        else:
            offer.offer_property_address = Address.objects.create(**address_defaults)
            offer.is_save_from_salesforce = True
            offer.save()


def sync_homeward_purchase_transaction_record_from_salesforce(salesforce_data):
    logger.info("Salesforce payload for sync_homeward_purchase_transaction_record_from_salesforce", extra=dict(
        type="sync_homeward_purchase_transaction_record_from_salesforce",
        data=salesforce_data
    ))

    if not salesforce_data.get(Offer.OFFER_TRANSACTION_ID):
        raise KeyError('Related Offer ID to Homeward Purchase is not provided')

    try:
        offer = Offer.objects.get(salesforce_id=salesforce_data.get(Offer.OFFER_TRANSACTION_ID))
    except Offer.DoesNotExist:
        logger.warning(f"No offer for salesforce ID: {salesforce_data.get(Offer.OFFER_TRANSACTION_ID)}",
                       extra=dict(
                           type="no_offer_for_given_sf_id",
                           salesforce_id=salesforce_data.get(Offer.OFFER_TRANSACTION_ID),
                           salesforce_data=salesforce_data
                       ))
        return

    new_option_end_date = salesforce_data.get(NewHomePurchase.OPTION_END_DATE_FIELD)
    new_homeward_purchase_close_date = salesforce_data.get(NewHomePurchase.NEW_HOME_PURCHASE_CLOSE_DATE)
    new_contract_price = salesforce_data.get(NewHomePurchase.CONTRACT_PRICE_TRANSACTION_FIELD)
    new_earnest_deposit_percentage = salesforce_data.get(NewHomePurchase.EARNEST_DEPOSIT_PERCENTAGE_FIELD)
    new_homeward_purchase_status = salesforce_data.get(NewHomePurchase.NEW_HOME_PURCHASE_STATUS)
    new_is_reassigned_contract = salesforce_data.get(NewHomePurchase.REASSIGNED_CONTRACT_FIELD)

    new_home_purchase = offer.new_home_purchase

    if new_home_purchase:
        new_home_purchase.option_period_end_date = new_option_end_date
        new_home_purchase.homeward_purchase_close_date = new_homeward_purchase_close_date
        new_home_purchase.contract_price = new_contract_price
        new_home_purchase.earnest_deposit_percentage = new_earnest_deposit_percentage
        new_home_purchase.homeward_purchase_status = new_homeward_purchase_status
        new_home_purchase.is_reassigned_contract = new_is_reassigned_contract

        new_home_purchase.save()
    else:
        offer.new_home_purchase = NewHomePurchase.objects.create(option_period_end_date=new_option_end_date,
                                                                 homeward_purchase_close_date=new_homeward_purchase_close_date,
                                                                 contract_price=new_contract_price,
                                                                 earnest_deposit_percentage=new_earnest_deposit_percentage,
                                                                 homeward_purchase_status=new_homeward_purchase_status,
                                                                 is_reassigned_contract=new_is_reassigned_contract)
        offer.save()


def sync_customer_purchase_transaction_record_from_salesforce(salesforce_data):
    logger.info("Salesforce payload for sync_customer_purchase_transaction_record_from_salesforce", extra=dict(
        type="sync_customer_purchase_transaction_record_from_salesforce",
        data=salesforce_data
    ))

    if not salesforce_data.get(Offer.OFFER_TRANSACTION_ID):
        raise KeyError('Related Offer ID to Customer Purchase is not provided')

    try:
        offer = Offer.objects.get(salesforce_id=salesforce_data.get(Offer.OFFER_TRANSACTION_ID))
    except Offer.DoesNotExist:
        logger.warning(f"No offer for salesforce ID: {salesforce_data.get(Offer.OFFER_TRANSACTION_ID)}",
                       extra=dict(
                           type="no_offer_for_given_sf_id",
                           salesforce_id=salesforce_data.get(Offer.OFFER_TRANSACTION_ID),
                           salesforce_data=salesforce_data
                       ))
        return

    if not offer.new_home_purchase:
        logger.warning(f"Unable to sync new home purchase for offer {offer.id}", extra=dict(
            type="no_new_home_purchase_for_given_offer_id",
            salesforce_id=salesforce_data.get(Offer.OFFER_TRANSACTION_ID),
            salesforce_data=salesforce_data,
            offer_id=offer.id
        ))
        return

    update_rent(offer.new_home_purchase, salesforce_data)

    new_customer_purchase_close_date = salesforce_data.get(NewHomePurchase.NEW_HOME_PURCHASE_CLOSE_DATE)
    new_customer_purchase_status = salesforce_data.get(NewHomePurchase.NEW_HOME_PURCHASE_STATUS)

    offer.new_home_purchase.customer_purchase_close_date = new_customer_purchase_close_date
    offer.new_home_purchase.customer_purchase_status = new_customer_purchase_status
    offer.new_home_purchase.save()


# TODO Removing after transition (CLOS-219)
@celery_app.task(queue='application-service-tasks')
def sync_customer_purchase_record_from_salesforce(salesforce_data):
    logger.info("Salesforce payload for sync_customer_purchase_record_from_salesforce", extra=dict(
        type="sync_customer_purchase_record_from_salesforce",
        data=salesforce_data
    ))

    if Rent.CUSTOMER_FIELD not in salesforce_data:
        raise KeyError('Customer field not provided in Rent SF sync')
    elif salesforce_data.get(Rent.CUSTOMER_FIELD) is None:
        raise ValueError('Customer field cannot be None')

    try:
        application = Application.objects.get(new_salesforce=salesforce_data.get(Rent.CUSTOMER_FIELD))
    except Application.DoesNotExist:
        logger.warning(f"No application for salesforce ID: {salesforce_data.get(Rent.CUSTOMER_FIELD)}", extra=dict(
            type="no_application_for_given_sf_id",
            salesforce_id=salesforce_data.get(Rent.CUSTOMER_FIELD),
            salesforce_data=salesforce_data
        ))
        return

    if not application.new_home_purchase:
        logger.warning(f"Unable to sync new home purchase for application {application.id}", extra=dict(
            type="no_new_home_purchase_for_given_application_id",
            salesforce_id=salesforce_data.get(Rent.CUSTOMER_FIELD),
            salesforce_data=salesforce_data,
            application_id=application.id
        ))
        return

    update_rent(application.new_home_purchase, salesforce_data)


@celery_app.task(queue='application-service-tasks')
def sync_record_from_salesforce(salesforce_data):
    logger.info("Salesforce Payload for sync_record_from_salesforce", extra=dict(
        type="salesforce_payload_sync_record_from_salesforce",
        data=salesforce_data))
    if Customer.EMAIL_FIELD not in salesforce_data:
        raise KeyError('Email not provided')
    application = Application.objects.filter(customer__email=salesforce_data[Customer.EMAIL_FIELD])
    if application.count() < 1:
        logger.warning(f"Can't find application for email: {salesforce_data[Customer.EMAIL_FIELD]}", extra=dict(
            type="no_application_for_given_email_sync_record_from_salesforce",
            email=salesforce_data[Customer.EMAIL_FIELD],
            data=salesforce_data,
        ))
        return
    elif application.count() > 1:
        logger.warning(f"Multiple applications for email: {salesforce_data[Customer.EMAIL_FIELD]}", extra=dict(
            type="multiple_applications_for_given_email_sync_record_from_salesforce",
            email=salesforce_data[Customer.EMAIL_FIELD],
            data=salesforce_data,
            application_id=application.id
        ))
        return
    application = application.first()
    customer = application.customer
    update_application(application, salesforce_data)
    update_customer(customer, salesforce_data)
    update_builder(application, salesforce_data)
    update_offer_property_address(application, salesforce_data)
    update_current_home(application, salesforce_data)
    update_lender(application, salesforce_data)
    update_real_estate_agent(application, salesforce_data)
    update_cx_manager(application, salesforce_data)
    update_loan_advisor(application, salesforce_data)
    update_stakeholders(application, salesforce_data)
    update_approval_specialist_on_application(application, salesforce_data)

    run_task_operations(Application.objects.get(id=application.id))


def update_application(application: Application, updated_application):
    new_move_in = updated_application.get(Application.TARGET_MOVE_DATE_FIELD)
    if new_move_in:
        application.move_in = new_move_in

    new_min_price = updated_application.get(Application.MIN_PRICE_FIELD)
    if new_min_price:
        application.min_price = new_min_price

    new_max_price = updated_application.get(Application.MAX_PRICE_FIELD)
    if new_max_price:
        application.max_price = new_max_price

    new_self_reported_referral_source = updated_application.get(Application.SELF_REPORTED_REFERRAL_SOURCE_FIELD)
    if new_self_reported_referral_source:
        application.self_reported_referral_source = new_self_reported_referral_source

    new_self_reported_referral_source_detail = updated_application.get(
        Application.SELF_REPORTED_REFERRAL_SOURCE_DETAIL_FIELD)
    if new_self_reported_referral_source_detail:
        application.self_reported_referral_source_detail = new_self_reported_referral_source_detail

    new_home_buying_stage = updated_application.get(Application.CUSTOMER_REPORTED_STAGE_FIELD)
    if new_home_buying_stage:
        application.home_buying_stage = new_home_buying_stage

    new_lead_source = updated_application.get(Application.LEAD_SOURCE_FIELD)
    if new_lead_source:
        application.lead_source = new_lead_source

    new_lead_source_drill_down_1 = updated_application.get(Application.LEAD_SOURCE_DETAIL_FIELD)
    if new_lead_source_drill_down_1:
        application.lead_source_drill_down_1 = new_lead_source_drill_down_1

    new_lead_status = updated_application.get(Application.LEAD_STATUS_FIELD)
    if new_lead_status:
        application.lead_status = new_lead_status

    new_stage = updated_application.get(Application.APPLICATION_STAGE_FIELD)
    if new_stage:
        application.stage = new_stage

    new_reason_for_trash = updated_application.get(Application.REASON_FOR_TRASH_FIELD)
    if new_reason_for_trash:
        application.reason_for_trash = new_reason_for_trash

    new_internal_referral = updated_application.get(Application.INTERNAL_REFERRAL_FIELD)
    if new_internal_referral:
        application.internal_referral = new_internal_referral

    new_blend_status = updated_application.get(Application.BLEND_STATUS_FIELD)
    if new_blend_status:
        application.blend_status = new_blend_status

    new_mortgage_loan_status = updated_application.get(Application.HOMEWARD_MORTGAGE_STATUS_FIELD)
    if new_mortgage_loan_status:
        application.mortgage_status = new_mortgage_loan_status

    new_owner_email = updated_application.get(Application.OWNER_EMAIL_FIELD)
    if new_owner_email:
        application.homeward_owner_email = new_owner_email

    new_product_offering = updated_application.get(Application.PRODUCT_OFFERING_FIELD)
    if new_product_offering:
        application.product_offering = new_product_offering.lower()

    new_hw_mortgage_candidate = updated_application.get(Application.HW_MORTGAGE_CANDIDATE)
    if new_hw_mortgage_candidate:
        application.hw_mortgage_candidate = new_hw_mortgage_candidate

    update_preapproval(application, updated_application)
    update_new_home_purchase(application, updated_application)

    application.save()


def update_preapproval(application: Application, salesforce_data: dict):
    new_amount = salesforce_data.get(PreApproval.PREAPPROVAL_AMOUNT_FIELD)
    new_estimated_down_payment = salesforce_data.get(PreApproval.ESTIMATED_DOWN_PAYMENT_AMOUNT_FIELD)
    new_vpal_approval_date = salesforce_data.get(PreApproval.VPAL_APPROVAL_DATE_FIELD)
    new_hw_mortgage_conditions = salesforce_data.get(PreApproval.HW_MORTGAGE_CONDITIONS)

    if application.preapproval is not None:
        preapproval = application.preapproval
        preapproval.amount = new_amount
        preapproval.estimated_down_payment = new_estimated_down_payment
        preapproval.vpal_approval_date = new_vpal_approval_date
        preapproval.hw_mortgage_conditions = new_hw_mortgage_conditions
        preapproval.save()
    elif any(elem is not None for elem in
             [new_amount, new_estimated_down_payment, new_vpal_approval_date, new_hw_mortgage_conditions]):
        application.preapproval = PreApproval.objects.create(amount=new_amount,
                                                             estimated_down_payment=new_estimated_down_payment,
                                                             vpal_approval_date=new_vpal_approval_date,
                                                             hw_mortgage_conditions=new_hw_mortgage_conditions)
        application.save()


def update_new_home_purchase(application: Application, salesforce_data: dict):
    new_option_end_date = salesforce_data.get(NewHomePurchase.OPTION_END_DATE_FIELD)
    new_homeward_purchase_close_date = salesforce_data.get(NewHomePurchase.HOMEWARD_PURCHASE_CLOSE_DATE_FIELD)
    new_homeward_purchase_status = salesforce_data.get(NewHomePurchase.NEW_HOME_PURCHASE_STATUS)
    new_customer_purchase_close_date = salesforce_data.get(NewHomePurchase.CUSTOMER_PURCHASE_CLOSE_DATE_FIELD)
    new_contract_price = salesforce_data.get(NewHomePurchase.CONTRACT_PRICE_FIELD)
    new_earnest_deposit_percentage = salesforce_data.get(NewHomePurchase.EARNEST_DEPOSIT_PERCENTAGE_FIELD)
    new_address_street = salesforce_data.get(Address.OFFER_ADDRESS_STREET_FIELD)
    new_address_city = salesforce_data.get(Address.OFFER_ADDRESS_CITY_FIELD)
    new_address_state = salesforce_data.get(Address.OFFER_ADDRESS_STATE_FIELD)
    new_address_zipcode = salesforce_data.get(Address.OFFER_ADDRESS_ZIP_FIELD)
    new_address_unit = salesforce_data.get(Address.OFFER_ADDRESS_UNIT_FIELD)
    new_is_reassigned_contract = salesforce_data.get(Application.REASSIGNED_CONTRACT_FIELD, False)

    new_home_purchase = application.new_home_purchase
    if new_home_purchase:
        new_home_purchase.option_period_end_date = new_option_end_date
        new_home_purchase.homeward_purchase_close_date = new_homeward_purchase_close_date
        new_home_purchase.homeward_purchase_status = new_homeward_purchase_status
        new_home_purchase.customer_purchase_close_date = new_customer_purchase_close_date
        new_home_purchase.contract_price = new_contract_price
        new_home_purchase.earnest_deposit_percentage = new_earnest_deposit_percentage
        new_home_purchase.is_reassigned_contract = new_is_reassigned_contract

        if new_home_purchase.address:
            address = new_home_purchase.address
            address.street = new_address_street
            address.city = new_address_city
            address.state = new_address_state
            address.zip = new_address_zipcode
            address.unit = new_address_unit
            address.save()
        elif (any(elem is not None for elem in [new_address_street, new_address_city, new_address_state,
                                                new_address_zipcode])):
            new_home_purchase.address = Address.objects.create(street=new_address_street, city=new_address_city,
                                                               state=new_address_state, zip=new_address_zipcode)

        new_home_purchase.save()
    elif any(elem is not None for elem in [new_option_end_date, new_homeward_purchase_close_date]):
        application.new_home_purchase = NewHomePurchase.objects.create(option_period_end_date=new_option_end_date,
                                                                       homeward_purchase_close_date=
                                                                       new_homeward_purchase_close_date,
                                                                       homeward_purchase_status=
                                                                       new_homeward_purchase_status,
                                                                       customer_purchase_close_date=
                                                                       new_customer_purchase_close_date,
                                                                       contract_price=new_contract_price,
                                                                       earnest_deposit_percentage=
                                                                       new_earnest_deposit_percentage,
                                                                       is_reassigned_contract=
                                                                       new_is_reassigned_contract)
        if (any(elem is not None for elem in [new_address_street, new_address_city, new_address_state,
                                              new_address_zipcode])):
            application.new_home_purchase.address = Address.objects.create(street=new_address_street,
                                                                           city=new_address_city,
                                                                           state=new_address_state,
                                                                           zip=new_address_zipcode)
            application.new_home_purchase.save()
        application.save()
    else:
        return


def update_rent(new_home_purchase: NewHomePurchase, salesforce_data: dict):
    new_rent_type = salesforce_data.get(Rent.RENT_PAYMENT_TYPE_FIELD)
    new_amount_months_one_and_two = salesforce_data.get(Rent.RENT_MONTHLY_RENTAL_RATE)
    daily_rental_rate = salesforce_data.get(Rent.RENT_DAILY_RENTAL_RATE)
    stop_rent_date = salesforce_data.get(Rent.RENT_STOP_DATE)
    total_waived_rent = salesforce_data.get(Rent.RENT_TOTAL_WAIVED_RENT)
    total_leaseback_credit = salesforce_data.get(Rent.RENT_TOTAL_LEASEBACK_CREDIT)

    rent = new_home_purchase.rent
    if all(elem is not None for elem in [new_rent_type, new_amount_months_one_and_two, daily_rental_rate]):
        if rent:
            rent.type = new_rent_type
            rent.daily_rental_rate = daily_rental_rate
            rent.amount_months_one_and_two = new_amount_months_one_and_two
            rent.stop_rent_date = stop_rent_date
            rent.total_waived_rent = total_waived_rent
            rent.total_leaseback_credit = total_leaseback_credit
            rent.save()
        else:
            new_home_purchase.rent = Rent.objects.create(type=new_rent_type,
                                                         daily_rental_rate=daily_rental_rate,
                                                         amount_months_one_and_two=new_amount_months_one_and_two,
                                                         stop_rent_date=stop_rent_date,
                                                         total_waived_rent=total_waived_rent,
                                                         total_leaseback_credit=total_leaseback_credit)
            new_home_purchase.save()


def update_customer(customer, updated_application):
    last_name_minus_not_provided = updated_application.get(Customer.LAST_NAME_FIELD, '') \
        .replace('NotProvided', '')
    customer.name = "{} {}".format(updated_application.get(Customer.FIRST_NAME_FIELD, ''),
                                   last_name_minus_not_provided)
    if Customer.PHONE_FIELD in updated_application:
        customer.phone = updated_application.get(Customer.PHONE_FIELD)
    if customer.CO_BORROWER_EMAIL_FIELD in updated_application:
        customer.co_borrower_email = updated_application.get(Customer.CO_BORROWER_EMAIL_FIELD)
    customer.save()


def update_builder(application, updated_application):
    builder: Builder = Builder.objects.filter(pk=application.builder.id).first() if application.builder else None
    if builder is not None:
        new_builder_name = updated_application.get(Builder.BUILDER_COMPANY_FIELD)
        if new_builder_name:
            builder.company_name = new_builder_name

        if updated_application.get(Builder.BUILDER_FIRST_NAME) or \
                updated_application.get(Builder.BUILDER_LAST_NAME):
            new_builder_name = "{} {}".format(updated_application.get(Builder.BUILDER_FIRST_NAME, ''),
                                              updated_application.get(Builder.BUILDER_LAST_NAME, ''))
            builder.representative_name = new_builder_name

        new_builder_email = updated_application.get(Builder.BUILDER_EMAIL)
        if new_builder_email:
            builder.representative_email = new_builder_email

        new_builder_phone = updated_application.get(Builder.BUILDER_PHONE)
        if new_builder_phone:
            builder.representative_phone = new_builder_phone

        builder.save()
    elif any(elem in updated_application
             for elem in [Builder.BUILDER_FIRST_NAME, Builder.BUILDER_LAST_NAME,
                          Builder.BUILDER_COMPANY_FIELD, Builder.BUILDER_EMAIL,
                          Builder.BUILDER_PHONE]):
        builder = Builder.objects.create(
            company_name=updated_application.get(Builder.BUILDER_COMPANY_FIELD),
            representative_name="{} {}".format(updated_application.get(Builder.BUILDER_FIRST_NAME, ''),
                                               updated_application.get(Builder.BUILDER_LAST_NAME, '')),
            representative_email=updated_application.get(Builder.BUILDER_EMAIL),
            representative_phone=updated_application.get(Builder.BUILDER_PHONE)
        )
        application.builder = builder
        application.save()


def update_offer_property_address(application: Application, salesforce_data) -> None:
    if any(elem in salesforce_data for elem in
           [Address.OFFER_ADDRESS_STREET_FIELD, Address.OFFER_ADDRESS_CITY_FIELD,
            Address.OFFER_ADDRESS_STATE_FIELD, Address.OFFER_ADDRESS_ZIP_FIELD, Address.OFFER_ADDRESS_UNIT_FIELD]):
        new_address_data = {
            'street': salesforce_data.get(Address.OFFER_ADDRESS_STREET_FIELD),
            'city': salesforce_data.get(Address.OFFER_ADDRESS_CITY_FIELD),
            'state': salesforce_data.get(Address.OFFER_ADDRESS_STATE_FIELD),
            'zip': salesforce_data.get(Address.OFFER_ADDRESS_ZIP_FIELD),
            'unit': salesforce_data.get(Address.OFFER_ADDRESS_UNIT_FIELD)
        }

        if application.offer_property_address:
            offer_property_address = Address.objects.filter(id=application.offer_property_address.id)
            offer_property_address.update(**new_address_data)
        else:
            application.offer_property_address = Address.objects.create(**new_address_data)
            application.save()


def get_or_create_agent_from_salesforce(sf_id: str):
    data = homeward_salesforce.get_account_by_id(sf_id)
    defaults = {
        'name': f"{data.get(Customer.FIRST_NAME_FIELD, '')} {data.get(Customer.LAST_NAME_FIELD, '')}",
        'phone': data.get(Customer.PHONE_FIELD),
        'email': data.get(Customer.EMAIL_FIELD),
        'company': data.get(RealEstateAgent.BUYING_AGENT_COMPANY_FIELD)
    }

    agent, _ = RealEstateAgent.objects.get_or_create(sf_id=sf_id, defaults=defaults)
    return agent


def update_agent_from_salesforce(agent: RealEstateAgent, sf_id: str):
    data = homeward_salesforce.get_account_by_id(sf_id)
    agent.name = f"{data.get(Customer.FIRST_NAME_FIELD, '')} {data.get(Customer.LAST_NAME_FIELD, '')}"
    agent.phone = data.get(Customer.PHONE_FIELD)
    agent.email = data.get(Customer.EMAIL_FIELD)
    agent.company = data.get(RealEstateAgent.BUYING_AGENT_COMPANY_FIELD)
    if data.get(Brokerage.BROKERAGE_ID_FIELD):
        sf_data = homeward_salesforce.get_account_by_id(data.get(Brokerage.BROKERAGE_ID_FIELD))
        defaults = {
            'name': sf_data.get(RealEstateAgent.NAME_FIELD),
            'partnership_status': sf_data.get(Brokerage.BROKER_PARTNERSHIP_STATUS_FIELD)
        }
        agent.brokerage, _ = Brokerage.objects.get_or_create(sf_id=data.get(Brokerage.BROKERAGE_ID_FIELD),
                                                             defaults=defaults)
    agent.save()


def update_real_estate_agent(application, updated_application):
    """
    Updates the application's listing and buying agents to those supplied in the updated_application
        from SalesForce. In the case of an update we gets or creates a new agent record rather than overwriting
        the existing record.
    """
    application_changed = False
    sf_listing_agent_id = updated_application.get(RealEstateAgent.LISTING_AGENT_ID_FIELD)
    if sf_listing_agent_id is not None:
        if application.listing_agent is None or \
                (application.listing_agent is not None and sf_listing_agent_id != application.listing_agent.sf_id):
            application.listing_agent = get_or_create_agent_from_salesforce(sf_listing_agent_id)
            application_changed = True

    sf_buying_agent_id = updated_application.get(RealEstateAgent.BUYING_AGENT_ID_FIELD)
    if sf_buying_agent_id is not None:
        if application.buying_agent is None or \
                (application.buying_agent is not None and sf_buying_agent_id != application.buying_agent.sf_id):
            application.buying_agent = get_or_create_agent_from_salesforce(sf_buying_agent_id)
            application_changed = True

    if application_changed:
        application.save()


def update_or_create_internal_support_user_from_salesforce(sf_user: dict):
    defaults = {
        'email': sf_user.get(InternalSupportUser.USER_EMAIL),
        'first_name': sf_user.get(InternalSupportUser.USER_FIRST_NAME),
        'last_name': sf_user.get(InternalSupportUser.USER_LAST_NAME),
        'phone': sf_user.get(InternalSupportUser.USER_PHONE),
        'photo_url': sf_user.get(InternalSupportUser.USER_PHOTO_URL),
        'bio': sf_user.get(InternalSupportUser.USER_BIO),
        'schedule_a_call_url': sf_user.get(InternalSupportUser.USER_SCHEDULE_A_CALL_URL)
    }
    sf_id = sf_user.get(InternalSupportUser.ID_FIELD)
    return InternalSupportUser.objects.update_or_create(sf_id=sf_id, defaults=defaults)


def update_cx_manager(application, salesforce_payload):
    sf_owner_user_id = salesforce_payload.get(InternalSupportUser.OWNER_ID_FIELD)

    if sf_owner_user_id:
        owner_sf_user = homeward_salesforce.get_user_by_id(sf_owner_user_id)

        # If record owner is a cx run update cx operations
        if owner_sf_user and \
                owner_sf_user.get(InternalSupportUser.USER_PROFILE_NAME) is not None and \
                "cx" in owner_sf_user.get(InternalSupportUser.USER_PROFILE_NAME).lower():
            cx_manager, _ = update_or_create_internal_support_user_from_salesforce(owner_sf_user)
            application.cx_manager = cx_manager
            application.save()


def update_loan_advisor(application, salesforce_payload):
    sf_loan_advisor_id = salesforce_payload.get(InternalSupportUser.LOAN_ADVISOR_ID_FIELD)

    if sf_loan_advisor_id is not None:
        loan_advisor_sf_user = homeward_salesforce.get_user_by_id(sf_loan_advisor_id)

        if loan_advisor_sf_user:
            loan_advisor, _ = update_or_create_internal_support_user_from_salesforce(loan_advisor_sf_user)
            application.loan_advisor = loan_advisor
            application.save()


def update_stakeholders(application, salesforce_payload):
    """
    Handles updating an applications stakeholders from salesforce data.
    """
    sf_tc_email = salesforce_payload.get(Application.BUY_AGENT_TRANSACTION_COORDINATOR_EMAIL)
    current_tc = application.stakeholders.filter(type=StakeholderType.TRANSACTION_COORDINATOR).first()
    if sf_tc_email is not None:
        if current_tc:
            if sf_tc_email == current_tc.email:
                return
            else:
                current_tc.delete()

        Stakeholder.objects.create(application=application, email=sf_tc_email,
                                   type=StakeholderType.TRANSACTION_COORDINATOR)


def update_lender(application, updated_application):
    new_lender_name = updated_application.get(MortgageLender.LENDER_FULL_NAME_FIELD)
    new_lender_email = updated_application.get(MortgageLender.LENDER_EMAIL_FIELD)
    new_lender_phone = updated_application.get(MortgageLender.LENDER_PHONE_FIELD)

    existing_lender = application.mortgage_lender

    if existing_lender:
        if new_lender_email:
            existing_lender.email = new_lender_email
        if new_lender_name:
            existing_lender.name = new_lender_name
        if new_lender_phone:
            existing_lender.phone = new_lender_phone
        existing_lender.save()
    elif any([new_lender_name, new_lender_phone, new_lender_email]):
        lender = MortgageLender.objects.create(
            email=new_lender_email,
            name=new_lender_name,
            phone=new_lender_phone
        )
        application.mortgage_lender = lender
        application.save()


def update_current_home(application, updated_application):
    current_home = application.current_home

    if current_home is not None:
        address = current_home.address
        if updated_application.get(Address.BILLING_STREET_FIELD):
            address.street = updated_application.get(Address.BILLING_STREET_FIELD)
        if updated_application.get(Address.BILLING_CITY_FIELD):
            address.city = updated_application.get(Address.BILLING_CITY_FIELD)
        if updated_application.get(Address.BILLING_STATE_FIELD):
            address.state = updated_application.get(Address.BILLING_STATE_FIELD)
        if updated_application.get(Address.BILLING_POSTAL_CODE_FIELD):
            address.zip = updated_application.get(Address.BILLING_POSTAL_CODE_FIELD)
        if updated_application.get(Address.BILLING_UNIT_FIELD):
            address.unit = updated_application.get(Address.BILLING_UNIT_FIELD)
        address.save()

        if updated_application.get(CurrentHome.OUTSTANDING_LOAN_AMOUNT_FIELD):
            current_home.outstanding_loan_amount = updated_application.get(CurrentHome.OUTSTANDING_LOAN_AMOUNT_FIELD)
        if updated_application.get(CurrentHome.CURRENT_HOME_MARKET_VALUE_FIELD):
            current_home.market_value = updated_application.get(CurrentHome.CURRENT_HOME_MARKET_VALUE_FIELD)

        update_floor_price(current_home, updated_application)
        current_home.save()

    elif any(elem in updated_application
             for elem in [Address.BILLING_STREET_FIELD, Address.BILLING_CITY_FIELD,
                          Address.BILLING_STATE_FIELD, Address.BILLING_POSTAL_CODE_FIELD, Address.BILLING_UNIT_FIELD]):
        address = Address.objects.create(street=updated_application.get(Address.BILLING_STREET_FIELD),
                                         city=updated_application.get(Address.BILLING_CITY_FIELD),
                                         state=updated_application.get(Address.BILLING_STATE_FIELD),
                                         zip=updated_application.get(Address.BILLING_POSTAL_CODE_FIELD),
                                         unit=updated_application.get(Address.BILLING_UNIT_FIELD))
        current_home = CurrentHome.objects.create(address=address, outstanding_loan_amount=updated_application
                                                  .get(CurrentHome.OUTSTANDING_LOAN_AMOUNT_FIELD),
                                                  market_value=updated_application.get(
                                                      CurrentHome.CURRENT_HOME_MARKET_VALUE_FIELD))
        application.current_home = current_home
        application.save()


def update_floor_price(current_home, salesforce_data):
    new_floor_price_type = salesforce_data.get(FloorPrice.FLOOR_PRICE_TYPE_FIELD)
    new_floor_price_amount = salesforce_data.get(FloorPrice.FLOOR_PRICE_AMOUNT_FIELD)
    new_preliminary_floor_price = salesforce_data.get(FloorPrice.PRELIMINARY_FLOOR_PRICE_FIELD)
    if any(elem is not None for elem in [new_floor_price_type, new_floor_price_amount, new_preliminary_floor_price]):
        floor_price = current_home.floor_price
        if floor_price is not None:
            floor_price.type = new_floor_price_type
            floor_price.amount = new_floor_price_amount
            floor_price.save()
        else:
            current_home.floor_price = FloorPrice.objects.create(type=new_floor_price_type,
                                                                 amount=new_floor_price_amount,
                                                                 preliminary_amount=new_preliminary_floor_price)
            current_home.save()
