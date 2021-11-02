import json


import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict

from celery.task import periodic_task
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from event_consumer import message_handler

from application.application_acknowledgements import add_acknowledgements
from application.email_trigger_tasks import send_registered_client_notification
from application.generate_pdf_task import ProcessPdf
from application.models.application import (BUILDER, FAST_TRACK_REGISTRATION,
                                            REAL_ESTATE_AGENT, REFERRAL_LINK,
                                            REGISTERED_CLIENT, LOAN_ADVISOR_FAST_TRACK, LOAN_ADVISOR,
                                            HomeBuyingStage,
                                            ProductOffering,
                                            SelfReportedReferralSource)
from application.models.builder import Builder
from application.models.customer import Customer
from application.models.models import (Address, Application, ApplicationStage,
                                       CurrentHome, CurrentHomeImage)
from application.models.mortgage_lender import MortgageLender
from application.models.notification import Notification
from application.models.notification_status import NotificationStatus
from application.models.pricing import Pricing
from application.models.real_estate_agent import AgentType, RealEstateAgent
from application.models.real_estate_lead import RealEstateLead
from application.task_operations import run_task_operations
from user.models import User
from utils import aws, hubspot, mailer
from utils.celery import app as celery_app
from utils.salesforce import (SalesforceException,
                              homeward_salesforce)
from utils.agent_svc_client import AgentServiceClient, AgentServiceClientException

logger = logging.getLogger(__name__)


def convert_response_to_application(body):
    response = json.loads(body)
    questionnaire_response = response['response']
    if questionnaire_response.get('email'):
        email = questionnaire_response.get('email').lower()

        existing_applications = Application.objects.filter(customer__email=email)
        if existing_applications.count() > 1:
            raise Exception("found {} applications for email {}, expected 1".format(existing_applications.count(), email))
        elif existing_applications.count() == 1:
            existing_application = existing_applications.first()
            update_customer(existing_application.customer, questionnaire_response)
            update_current_home(existing_application, questionnaire_response)
            logger.info("Updating response to existing application", extra=dict(
                type="updating_response_to_existing_application",
                response_id=response.get('id'),
                existing_application_id=existing_application.id,
                pricing_id=questionnaire_response.get('pricing_estimate_id'),
                email=questionnaire_response.get('email')
            ))
            update_application(existing_application, response)
        else:
            customer = create_customer(questionnaire_response)
            current_home = create_current_home(questionnaire_response)
            new_application_id = create_application(customer, current_home, response)
            logger.info("Converting response to new application", extra=dict(
                type="converting_response_to_new_application",
                response_id=response.get('id'),
                new_application_id=new_application_id,
                pricing_id=questionnaire_response.get('pricing_estimate_id'),
                email=questionnaire_response.get('email')
            ))
    elif questionnaire_response.get('pricing_estimate_id'):
        agent = get_or_create_agent_from_response(questionnaire_response)
        pricing = Pricing.objects.get(id=questionnaire_response.get('pricing_estimate_id'))
        pricing.agent = agent
        pricing.questionnaire_response_id = response.get("id")
        logger.info("Updating Pricing object from response", extra=dict(
            type="updating_pricing_object_from_response",
            response=response,
            pricing_id=pricing.id,
            email=questionnaire_response.get('email')
        ))
        pricing.save()


def get_or_create_agent_from_response(questionnaire_response) -> RealEstateAgent:
    agent_id = questionnaire_response.get('certified_agent_id') or questionnaire_response.get('agent_id')
    defaults = {
        'name': f"{questionnaire_response.get('agents_first_name')} {questionnaire_response.get('agents_last_name')}",
        'phone': questionnaire_response.get('agents_phone_number'),
        'email': questionnaire_response.get('agents_email'),
        'company': questionnaire_response.get('agents_company'),
        'self_reported_referral_source': questionnaire_response.get('agent_self_reported_referral_source'),
        'self_reported_referral_source_detail': questionnaire_response.get('agent_self_reported_referral_source')
    }

    agent, _ = RealEstateAgent.objects.get_or_create(id=agent_id, defaults=defaults)

    return agent


def create_customer(questionnaire_response):
    name = get_name_from_response(questionnaire_response)
    defaults = {
        'name': name,
        'email': questionnaire_response.get('email').lower(),
        'phone': questionnaire_response.get('phone_number')
    }

    customer = Customer.objects.create(**defaults)

    return customer


def update_customer(customer: Customer, questionnaire_response: Dict[str, str]):
    customer.name = get_name_from_response(questionnaire_response)
    customer.email = questionnaire_response.get('email').lower()
    customer.phone = questionnaire_response.get('phone_number')
    customer.save()


def get_name_from_response(questionnaire_response) -> str:
    if questionnaire_response.get('first_name') or questionnaire_response.get('last_name'):
        return "{} {}".format(questionnaire_response.get('first_name'), questionnaire_response.get('last_name'))
    elif questionnaire_response.get('name'):
        return questionnaire_response.get('name')
    else:
        logger.error("Missing first/last name, or none specified. Setting to blank", extra=dict(
            type="setting_field_missing_info_from_response_to_blank",
            questionnaire_response_id=questionnaire_response.id,
        ))
        return ""


def create_current_home(questionnaire_response: Dict[str, str]):
    if questionnaire_response.get('do_you_have_a_home_to_sell') == 'yes' and \
            questionnaire_response.get("whats_the_address_of_the_home_youre_selling"):

        home_address = questionnaire_response.get("whats_the_address_of_the_home_youre_selling")
        if 'address' in home_address:
            home_address = home_address['address']
        street = home_address['street_address']
        unit = home_address.get('unit', None)
        city = home_address['city']
        state = home_address['state']
        zipcode = home_address['postcode']

        address = Address.objects.create(street=street, city=city, state=state, zip=zipcode, unit=unit)
        current_home_defaults = {
            'address': address
        }
        current_home = CurrentHome.objects.create(**current_home_defaults)
        return set_current_home_attributes(current_home, questionnaire_response)
    elif questionnaire_response.get('do_you_have_a_home_to_sell') == 'no':
        # do nothing!
        return
    return

def text_binary_response_to_bool(response_text: str):
    if response_text == 'yes':
        return True
    elif response_text == 'no':
        return False

def get_int_or_none(response_text):
    if response_text:
        try:
            return int(response_text)
        except Exception as e:
            logger.exception("Problem parsing value from payload to int", exc_info=e, extra=dict(
                type="parse_error_from_payload_to_int",
                response_text=response_text
            ))
            return None

def get_float_or_none(response_text):
    if response_text:
        try:
            return float(response_text)
        except Exception as e:
            logger.exception("Problem parsing value from payload to float", exc_info=e, extra=dict(
                type="parse_error_from_payload_to_float",
                response_text=response_text
            ))
    return None

def set_current_home_attributes(current_home: CurrentHome, questionnaire_response: Dict[str, str]):
    current_home.outstanding_loan_amount = get_float_or_none(questionnaire_response \
        .get('what_is_the_balance_of_all_outstanding_loans_against_this_property'))

    current_home.customer_value_opinion = questionnaire_response.get('how_much_you_think_your_home_is_worth_today')

    closing_date = questionnaire_response.get('closing_date')
    if closing_date:
        closing_date = datetime.strptime(closing_date, "%Y-%m-%d").date()

    option_period_expiration_date = questionnaire_response.get('option_period_expiration_date')
    if option_period_expiration_date:
        option_period_expiration_date = datetime.strptime(option_period_expiration_date, "%Y-%m-%d").date()

    current_home.listing_status = questionnaire_response.get('is_your_home_listed_or_under_contract')
    current_home.listing_url = questionnaire_response.get('listing_url')
    current_home.total_concession_amount = get_float_or_none(questionnaire_response.get('total_concession_amount'))
    current_home.option_period_expiration_date = option_period_expiration_date
    current_home.closing_date = closing_date
    current_home.floors_count = get_int_or_none(questionnaire_response.get('how_many_floors_does_it_have'))
    current_home.bedrooms_count = get_int_or_none(questionnaire_response.get('how_many_bedrooms_does_it_have'))
    current_home.master_on_main = text_binary_response_to_bool(questionnaire_response.get('is_the_master_bedroom_on_the_main_floor'))
    current_home.home_size_sq_ft = get_int_or_none(questionnaire_response.get('how_big_is_your_home'))
    current_home.has_made_addition = text_binary_response_to_bool(questionnaire_response.get('have_you_made_any_additions'))
    current_home.addition_type = questionnaire_response.get('were_the_additions_permitted_or_unpermitted')
    current_home.addition_size_sq_ft = get_int_or_none(questionnaire_response.get('how_much_area_was_added_with_the_addition'))
    current_home.has_basement = questionnaire_response.get('does_your_home_have_a_basement')
    current_home.basement_type = questionnaire_response.get('is_the_basement_finished_or_unfinished')
    current_home.basement_size_sq_ft = get_int_or_none(questionnaire_response.get('basement_square_footage'))
    current_home.kitchen_countertop_type = questionnaire_response.get('what_type_of_countertops_does_your_kitchen_have')
    current_home.kitchen_appliance_type = questionnaire_response.get('what_type_of_kitchen_appliances_do_you_have')
    current_home.kitchen_features = questionnaire_response.get('does_your_kitchen_have_any_of_these_features')
    current_home.kitchen_has_been_remodeled = questionnaire_response.get('have_you_remodeled_your_kitchen_since_you_purchased_your_home')
    current_home.master_bathroom_condition = questionnaire_response.get('how_would_you_describe_the_condition_of_your_master_bathroom')
    current_home.full_bathrooms_count = get_int_or_none(questionnaire_response.get('how_many_full_bathrooms_in_your_home'))
    current_home.partial_bathrooms_count = get_int_or_none(questionnaire_response.get('how_many_partial_bathrooms_in_your_home'))
    current_home.interior_walls_condition = questionnaire_response.get('what_is_the_condition_of_the_interior_walls')
    current_home.flooring_types = questionnaire_response.get('what_type_of_flooring_do_you_have_in_your_home')
    current_home.hardwood_flooring_condition = questionnaire_response.get('what_is_the_overall_condition_of_your_hardwood_flooring')
    current_home.carpet_flooring_condition = questionnaire_response.get('what_is_the_overall_condition_of_your_carpet_flooring')
    current_home.front_yard_condition = questionnaire_response.get('what_is_the_overall_condition_of_your_front_yard')
    current_home.back_yard_condition = questionnaire_response.get('what_is_the_overall_condition_of_your_back_yard')
    current_home.exterior_walls_types = questionnaire_response.get('what_type_of_exterior_walls_do_you_have')
    current_home.sides_with_masonry_count = questionnaire_response.get('how_many_sides_of_the_home_has_masonary_on_it')
    current_home.roof_age_range = questionnaire_response.get('how_old_is_the_roof')
    current_home.pool_type = questionnaire_response.get('what_type_of_pool_is_it')
    current_home.garage_spaces_count = questionnaire_response.get('how_many_garage_spaces')
    current_home.hvac_age_range = questionnaire_response.get('what_is_the_age_of_your_HVAC_system')
    current_home.home_features = questionnaire_response.get('does_your_home_have_any_of_the_following')
    current_home.in_floodzone = questionnaire_response.get('is_any_part_of_your_property_in_a_floodzone_area')
    current_home.property_view_type = questionnaire_response.get('does_your_property_have_a_view')
    current_home.repair_or_update_detail = questionnaire_response.get('repair_or_update_detail')
    current_home.customer_notes = questionnaire_response.get('anything_else_detail')
    current_home.under_contract_sales_price = get_float_or_none(questionnaire_response.get('under_contract_sales_price'))
    current_home.anything_needs_repairs = text_binary_response_to_bool(questionnaire_response.get('is_there_anything_that_needs_repair'))
    current_home.made_repairs_or_updates = text_binary_response_to_bool(questionnaire_response.get('have_you_made_any_repairs_or_updates'))
    current_home.save()

    return current_home


def update_current_home(application: Application, questionnaire_response: Dict[str, str]):
    if application.current_home is None:
        application.current_home = create_current_home(questionnaire_response)
        application.save()
    elif application.current_home:
        current_home = application.current_home
        if questionnaire_response.get("whats_the_address_of_the_home_youre_selling"):
            create_or_update_current_home_address_from_questionna_response(current_home, questionnaire_response)
        current_home = set_current_home_attributes(current_home, questionnaire_response)
        current_home.save()
    return


def create_or_update_current_home_address_from_questionna_response(current_home: CurrentHome, questionnaire_response):
    home_address = questionnaire_response.get("whats_the_address_of_the_home_youre_selling")
    if 'address' in home_address:
        home_address: dict = home_address.get('address')
    street = home_address['street_address']
    unit = home_address.get('unit', None)
    city = home_address['city']
    state = home_address['state']
    zip_code = home_address['postcode']
    if current_home.address:
        current_home.address.street = street
        current_home.address.city = city
        current_home.address.state = state
        current_home.address.zip = zip_code
        current_home.unit = unit
        current_home.address.save()
    else:
        address = Address.objects.create(street=street, city=city, state=state, zip=zip_code, unit=unit)
        current_home.address = address

def get_agent_id_from_agent_svc(agent_service_verified_sso_id):
    if agent_service_verified_sso_id:
        return AgentServiceClient().get_agent_id(agent_service_verified_sso_id)
    else:
        return None

def create_application(customer, current_home, response):  # noqa: C901
    agent_service_verified_sso_id = response.get("agent_service_verified_sso_id")
    agent_svc_id = get_agent_id_from_agent_svc(agent_service_verified_sso_id)
    questionnaire_response_id = response.get("id")
    questionnaire_response = response['response']
    home_buying_location = None
    looking_in = questionnaire_response.get("which_city_are_you_looking_in", '')
    if isinstance(looking_in, dict):
        shopping_location = looking_in.get("original_address", '')
        street = looking_in.get('street_address', None)
        unit = looking_in.get('unit', None)
        city = looking_in.get('city', None)
        state = looking_in.get('state', None)
        zip_code = looking_in.get('postcode', None)

        home_buying_location = Address.objects.create(street=street, city=city, state=state, zip=zip_code, unit=unit)
    else:
        shopping_location = ''

    if 'where_are_you_in_the_process' in questionnaire_response:
        home_buying_stage = HomeBuyingStage(questionnaire_response["where_are_you_in_the_process"])
    else:
        home_buying_stage = ''

    builder = None
    if home_buying_stage == HomeBuyingStage.BUILDER:
        builder_name = questionnaire_response.get("builders_company_name", '')
        builder_address = questionnaire_response.get("builders_address", '')

        if questionnaire_response.get("builder_rep_first_name") and questionnaire_response.get("builder_rep_last_name"):
            builder_rep_name = "{} {}".format(questionnaire_response.get("builder_rep_first_name"),
                                              questionnaire_response.get("builder_rep_last_name"))
        else:
            builder_rep_name = None
        builder_rep_email = questionnaire_response.get("builder_rep_email")
        builder_rep_phone = questionnaire_response.get("builder_rep_phone_number")
        builder_referral_source = questionnaire_response.get("builder_self_reported_referral_source")
        builder_referral_source_detail = questionnaire_response.get("builder_self_reported_referral_source_detail")

        street = None
        city = None
        state = None
        zip_code = None
        unit = None

        if isinstance(builder_address, dict):
            street = builder_address['street_address']
            unit = builder_address.get('unit', None)
            city = builder_address['city']
            state = builder_address['state']
            zip_code = builder_address['postcode']
        elif isinstance(builder_address, str):
            street = builder_address

        address = Address.objects.create(street=street, city=city, state=state, zip=zip_code, unit=unit)

        builder = Builder.objects.create(company_name=builder_name, address=address,
                                         representative_name=builder_rep_name, representative_email=builder_rep_email,
                                         representative_phone=builder_rep_phone,
                                         self_reported_referral_source=builder_referral_source,
                                         self_reported_referral_source_detail=builder_referral_source_detail)

    stage = ApplicationStage.from_str(response['status'])

    price_range = questionnaire_response.get('what_price_range_are_you_looking_in', {})
    min_price = price_range.get('min')
    max_price = price_range.get('max')

    move_in = questionnaire_response.get('when_are_you_looking_to_move')
    move_by_date = questionnaire_response.get('what_date_are_you_looking_to_move_by')

    internal_referral, internal_referral_detail = get_internal_referral_and_detail_from_referral_source(
        questionnaire_response.get("referral_source"), questionnaire_response.get("referral_source_detail"))

    agent = None
    if questionnaire_response.get('certified_agent_id') or questionnaire_response.get('agent_id'):
        agent_id = questionnaire_response.get('certified_agent_id') or questionnaire_response.get('agent_id')
        try:
            agent = RealEstateAgent.objects.get(id=agent_id)
        except ObjectDoesNotExist:
            logger.warning("User specified agent ID but not found", extra=dict(
                type="user_specified_agent_id_not_found_create_application",
                customer=customer.id,
                customer_email=customer.email,
                agent_id=agent_id,
                current_home=current_home.id
            ))
        except (ValueError, ValidationError):
            logger.error("Malformed Agent ID provided by user", extra=dict(
                type="malformed_agent_id_provided_create_application",
                agent_id=agent_id
            ))
    elif questionnaire_response.get("are_you_working_with_a_real_estate_agent") == 'yes':
        name = "{} {}".format(questionnaire_response.get("agents_first_name"),
                              questionnaire_response.get("agents_last_name"))
        phone = questionnaire_response.get('agents_phone_number')
        email = questionnaire_response.get('agents_email')
        company = questionnaire_response.get('agents_company')
        agent_self_reported_referral_source = questionnaire_response.get('agent_self_reported_referral_source')
        agent_srrs_detail = questionnaire_response.get('agent_self_reported_referral_source_detail')
        agent = RealEstateAgent.objects.create(name=name, phone=phone, email=email, company=company,
                                               self_reported_referral_source=agent_self_reported_referral_source,
                                               self_reported_referral_source_detail=agent_srrs_detail)

    lender = None
    if questionnaire_response.get("lenders_email"):
        working_with_lender = True
        name = "{} {}".format(questionnaire_response.get("lenders_first_name", ""),
                              questionnaire_response.get("lenders_last_name", ""))
        email = questionnaire_response.get("lenders_email", '')
        phone = questionnaire_response.get("lenders_phone_number", '')

        lenders = MortgageLender.objects.filter(name=name, email=email, phone=phone)
        if lenders.count() != 0:
            lender = lenders.first()
        else:
            lender = MortgageLender.objects.create(name=name, email=email, phone=phone)
    else:
        working_with_lender = None

    offer_property_address = None
    if "what_address_are_you_making_an_offer_on" in questionnaire_response:
        address = questionnaire_response.get("what_address_are_you_making_an_offer_on", {})

        street = None
        city = None
        state = None
        zipcode = None
        unit = None

        if isinstance(address, dict):
            shopping_location = address.get('city') + ", " + address.get('state') + ", USA"
            street = address.get('street_address')
            city = address.get('city')
            state = address.get('state')
            zipcode = address.get('postcode')
            unit = address.get('unit')
        elif isinstance(address, str):
            street = address

        offer_property_address = Address.objects.create(street=street, city=city, state=state, zip=zipcode, unit=unit)

    utm = response.get('utm', {})
    hubspot_context = questionnaire_response.get('hubspot_context', {})

    if hubspot_context == {}:
        logger.info("Hubspot context is null for this record", extra=dict(
            type="warning_null_hubspot_context_for_record_create_application",
            questionnaire_response_id=questionnaire_response_id
        ))

    self_reported_referral_source = questionnaire_response.get('self_reported_referral_source')

    try:
        if self_reported_referral_source:
            self_reported_referral_source = SelfReportedReferralSource(self_reported_referral_source)
    except ValueError:
        logger.error("Invalid self-reported referral source for customer", extra=dict(
            type="invalid_self_reported_referral_source_create_application",
            questionnaire_response_id=questionnaire_response_id,
            questionnaire_response_email=questionnaire_response.get('email'),
            self_reported_referral_source=self_reported_referral_source
        ))

    self_reported_referral_source_detail = questionnaire_response.get('self_reported_referral_source_detail')

    has_consented_to_receive_electronic_documents = \
        questionnaire_response.get('has_consented_to_receive_electronic_documents', False)

    if questionnaire_response.get('do_you_have_a_home_to_sell') == 'no':
        product_offering = ProductOffering.BUY_ONLY
    else:
        product_offering = ProductOffering.BUY_SELL

    agent_client_contact_preference = questionnaire_response.get('agent_client_contact_preference')
    apex_partner_slug = questionnaire_response.get('apex_partner_slug')
    salesforce_company_id = questionnaire_response.get('sf_company_id')

    application_defaults = {
        'customer': customer,
        'current_home': current_home,
        'shopping_location': shopping_location,
        'home_buying_stage': home_buying_stage,
        'stage': stage,
        'min_price': min_price,
        'max_price': max_price,
        'move_in': move_in,
        'move_by_date': move_by_date,
        # todo: delete real_estate_agent after migrating
        'real_estate_agent': agent,
        'listing_agent': agent,
        'buying_agent': agent,
        'mortgage_lender': lender,
        'builder': builder,
        'offer_property_address': offer_property_address,
        'hubspot_context': hubspot_context,
        'utm': utm,
        'self_reported_referral_source': self_reported_referral_source,
        'self_reported_referral_source_detail': self_reported_referral_source_detail,
        'home_buying_location': home_buying_location,
        'internal_referral': internal_referral,
        'internal_referral_detail': internal_referral_detail,
        'has_consented_to_receive_electronic_documents': has_consented_to_receive_electronic_documents,
        'needs_lender': working_with_lender is not None and not working_with_lender,
        "questionnaire_response_id": questionnaire_response_id,
        "agent_notes": questionnaire_response.get('agent_notes'),
        "product_offering": product_offering,
        "agent_client_contact_preference": agent_client_contact_preference,
        "apex_partner_slug": apex_partner_slug,
        "salesforce_company_id": salesforce_company_id,
        "agent_service_buying_agent_id": agent_svc_id
    }

    application = Application.objects.create(**application_defaults)

    if questionnaire_response.get('pricing_estimate_id'):
        pricing = Pricing.objects.get(pk=questionnaire_response.get('pricing_estimate_id'))
        pricing.application = application
        pricing.save()
        send_registered_client_notification.delay(application.id)

    add_acknowledgements(application)

    run_task_operations(application)

    push_to_salesforce.apply_async(kwargs={
        'application_id': application.pk
    })

    sync_with_hubspot.apply_async(kwargs={
        'application_id': application.pk
    })

    if internal_referral_detail == REFERRAL_LINK and application.listing_agent.is_certified:
        send_agent_referral_notification.apply_async(kwargs={
            'application_id': application.pk
        })
    elif internal_referral_detail == REGISTERED_CLIENT:
        send_agent_registration_notification.delay(application_id=application.pk)

    if stage == ApplicationStage.COMPLETE:
        update_app_status.apply_async(kwargs={
            'application_id': application.pk
        })

    return application.id


def get_internal_referral_and_detail_from_referral_source(referral_source: str, referral_source_detail=None):
    if referral_source == REAL_ESTATE_AGENT or referral_source == BUILDER:
        internal_referral = referral_source
        internal_referral_detail = REGISTERED_CLIENT
    elif referral_source == FAST_TRACK_REGISTRATION:
        internal_referral = REAL_ESTATE_AGENT
        internal_referral_detail = FAST_TRACK_REGISTRATION
    elif referral_source == REFERRAL_LINK:
        internal_referral = REAL_ESTATE_AGENT
        internal_referral_detail = REFERRAL_LINK
    elif referral_source == LOAN_ADVISOR_FAST_TRACK:
        internal_referral = LOAN_ADVISOR
        internal_referral_detail = FAST_TRACK_REGISTRATION
    else:
        internal_referral = referral_source
        internal_referral_detail = referral_source_detail
    return internal_referral, internal_referral_detail


def update_application(application: Application, response):  # noqa: C901
    questionnaire_response = response['response']
    looking_in = questionnaire_response.get("which_city_are_you_looking_in", '')
    if isinstance(looking_in, dict):
        street = looking_in.get('street_address')
        city = looking_in.get('city')
        state = looking_in.get('state')
        zip_code = looking_in.get('postcode')
        if application.home_buying_location:
            application.home_buying_location.street = street
            application.home_buying_location.city = city
            application.home_buying_location.state = state
            application.home_buying_location.zip = zip_code
            application.home_buying_location.save()
        else:
            application.home_buying_location = Address.objects.create(street=street, city=city, state=state,
                                                                      zip=zip_code)

    if 'where_are_you_in_the_process' in questionnaire_response:
        home_buying_stage = HomeBuyingStage(questionnaire_response["where_are_you_in_the_process"])
    else:
        logger.error("Home buying stage was not present for application", extra=dict(
            type="home_buying_stage_not_present_in_application",
            application_id=application.id,
            questionnaire_response=questionnaire_response
        ))
        home_buying_stage = None

    builder = application.builder
    if home_buying_stage == HomeBuyingStage.BUILDER:
        builder_name = questionnaire_response.get("builders_company_name")
        builder_address = questionnaire_response.get("builders_address")

        if questionnaire_response.get("builder_rep_first_name") and questionnaire_response.get("builder_rep_last_name"):
            builder_rep_name = "{} {}".format(questionnaire_response.get("builder_rep_first_name"),
                                              questionnaire_response.get("builder_rep_last_name"))
        else:
            builder_rep_name = None
        builder_rep_email = questionnaire_response.get("builder_rep_email")
        builder_rep_phone = questionnaire_response.get("builder_rep_phone_number")
        builder_referral_source = questionnaire_response.get("builder_self_reported_referral_source")
        builder_referral_source_detail = questionnaire_response.get("builder_self_reported_referral_source_detail")

        street = None
        city = None
        state = None
        zipcode = None

        if isinstance(builder_address, dict):
            street = builder_address['street_address']
            city = builder_address['city']
            state = builder_address['state']
            zipcode = builder_address['postcode']
        elif isinstance(builder_address, str):
            street = builder_address

        if builder:
            builder.company_name = builder_name
            builder.representative_name = builder_rep_name
            builder.representative_email = builder_rep_email
            builder.representative_phone = builder_rep_phone
            builder.self_reported_referral_source = builder_referral_source
            builder.self_reported_referral_source_detail = builder_referral_source_detail

            if builder.address:
                builder.address.street = street
                builder.address.city = city
                builder.address.state = state
                builder.address.zip = zipcode
                builder.address.save()
            else:
                builder.address = Address.objects.create(street=street, city=city, state=state, zip=zipcode)
            builder.save()
        else:
            address = Address.objects.create(street=street, city=city, state=state, zip=zipcode)
            application.builder = Builder.objects.create(company_name=builder_name, address=address,
                                                         representative_name=builder_rep_name,
                                                         representative_email=builder_rep_email,
                                                         representative_phone=builder_rep_phone,
                                                         self_reported_referral_source=builder_referral_source,
                                                         self_reported_referral_source_detail=builder_referral_source_detail)
    if application.stage == ApplicationStage.INCOMPLETE:
        application.stage = ApplicationStage.from_str(response['status'])

    price_range = questionnaire_response.get('what_price_range_are_you_looking_in', {})
    application.min_price = price_range.get('min')
    application.max_price = price_range.get('max')

    application.move_in = questionnaire_response.get('when_are_you_looking_to_move', '')

    if questionnaire_response.get('when_are_you_looking_to_move', '') == 'by a specific date':
        application.move_by_date = questionnaire_response['what_date_are_you_looking_to_move_by']

    application.internal_referral, application.internal_referral_detail = \
        get_internal_referral_and_detail_from_referral_source(questionnaire_response.get("referral_source"),
                                                              questionnaire_response.get("referral_source_detail"))

    if questionnaire_response.get('certified_agent_id') or questionnaire_response.get('agent_id'):
        try:
            agent_id = uuid.UUID(questionnaire_response.get('certified_agent_id') or
                                 questionnaire_response.get('agent_id'))
            application.listing_agent_id = agent_id
            application.buying_agent_id = agent_id
        except ObjectDoesNotExist:
            logger.warning("User specified agent ID but not found", extra=dict(
                type="user_specified_agent_id_not_found_update_application",
                application_id=application.id,
                questionnaire_response=questionnaire_response,
                response=response,
            ))
        except (ValueError, ValidationError):
            logger.error("Malformed Agent ID provided by user", extra=dict(
                type="malformed_agent_id_provided_update_application",
                certified_agent_id=questionnaire_response.get('certified_agent_id'),
                agent_id=questionnaire_response.get('agent_id'),
                questionnaire_response=questionnaire_response
            ))
    elif questionnaire_response.get("are_you_working_with_a_real_estate_agent") == 'yes':
        name = "{} {}".format(questionnaire_response.get("agents_first_name"),
                              questionnaire_response.get("agents_last_name"))
        phone = questionnaire_response.get('agents_phone_number')
        email = questionnaire_response.get('agents_email')
        company = questionnaire_response.get('agents_company')
        agent_self_reported_referral_source = questionnaire_response.get('agent_self_reported_referral_source')
        agent_srrs_detail = questionnaire_response.get('agent_self_reported_referral_source_detail')

        if application.real_estate_agent:
            application.real_estate_agent.name = name
            application.real_estate_agent.phone = phone
            application.real_estate_agent.email = email
            application.real_estate_agent.company = company
            application.real_estate_agent.self_reported_referral_source = agent_self_reported_referral_source
            application.real_estate_agent.self_reported_referral_source_detail = agent_srrs_detail
            application.real_estate_agent.save()
        else:
            application.real_estate_agent = RealEstateAgent.objects.create(name=name, phone=phone, email=email,
                                                                           company=company,
                                                                           self_reported_referral_source=agent_self_reported_referral_source,
                                                                           self_reported_referral_source_detail=agent_srrs_detail)

    if questionnaire_response.get("are_you_already_working_with_a_lender") == 'yes':
        application.needs_lender = False
        name = "{} {}".format(questionnaire_response.get("lenders_first_name", ""),
                              questionnaire_response.get("lenders_last_name", ""))
        email = questionnaire_response.get("lenders_email")
        phone = questionnaire_response.get("lenders_phone_number")

        if application.mortgage_lender:
            application.mortgage_lender.name = name
            application.mortgage_lender.email = email
            application.mortgage_lender.phone = phone
            application.mortgage_lender.save()
        else:
            application.mortgage_lender = MortgageLender.objects.create(name=name, email=email, phone=phone)
    elif questionnaire_response.get("are_you_already_working_with_a_lender", '') == 'no':
        application.needs_lender = True
    else:
        application.needs_lender = None

    if "what_address_are_you_making_an_offer_on" in questionnaire_response:
        address = questionnaire_response.get("what_address_are_you_making_an_offer_on", {})

        street = None
        city = None
        state = None
        zipcode = None
        unit = None

        if isinstance(address, dict):
            street = address['street_address']
            city = address['city']
            state = address['state']
            zipcode = address['postcode']
            unit = address.get('unit', None)
        elif isinstance(address, str):
            street = address

        if application.offer_property_address:
            application.offer_property_address.street = street
            application.offer_property_address.city = city
            application.offer_property_address.state = state
            application.offer_property_address.zip = zipcode
            application.offer_property_address.unit = unit
        else:
            application.offer_property_address = Address.objects.create(street=street, city=city, state=state,
                                                                        zip=zipcode, unit=unit)

    application.utm = response.get('utm', {})
    application.hubspot_context = questionnaire_response.get('hubspot_context', {})

    self_reported_referral_source = questionnaire_response.get('self_reported_referral_source')

    try:
        if self_reported_referral_source:
            self_reported_referral_source = SelfReportedReferralSource(self_reported_referral_source)
    except ValueError:
        logger.error("Invalid referral source for customer", extra=dict(
            type="invalid_referral_source_update_application",
            self_reported_referral_source=questionnaire_response.get('self_reported_referral_source'),
            application_id=application.id,
            customer_email=questionnaire_response.get('email')
        ))

    application.self_reported_referral_source = self_reported_referral_source

    application.self_reported_referral_source_detail = questionnaire_response.get(
        'self_reported_referral_source_detail')

    application.has_consented_to_receive_electronic_documents = \
        questionnaire_response.get('has_consented_to_receive_electronic_documents', False)

    if questionnaire_response.get('agent_client_contact_preference'):
        application.agent_client_contact_preference = questionnaire_response.get('agent_client_contact_preference')

    if questionnaire_response.get('apex_partner_slug'):
        application.apex_partner_slug = questionnaire_response.get('apex_partner_slug')

    if questionnaire_response.get('sf_company_id'):
        application.salesforce_company_id = questionnaire_response.get('sf_company_id')

    application.save()

    if questionnaire_response.get('pricing_estimate_id'):
        pricing = Pricing.objects.get(pk=questionnaire_response.get('pricing_estimate_id'))
        pricing.application = application
        pricing.save()

    application.agent_notes = questionnaire_response.get('agent_notes')

    add_acknowledgements(application)

    run_task_operations(application)

    push_to_salesforce.apply_async(kwargs={
        'application_id': application.pk
    })

    sync_with_hubspot.apply_async(kwargs={
        'application_id': application.pk
    })

    if application.stage == ApplicationStage.COMPLETE:
        update_app_status.apply_async(kwargs={
            'application_id': application.pk
        })


@celery_app.task(queue='application-service-tasks')
def sync_with_hubspot(application_id):
    application = Application.objects.get(pk=application_id)
    if application.pushed_to_hubspot_on is None:
        push_to_hubspot(application_id)

    if 'hutk' in application.hubspot_context:
        get_lead_source_from_hubspot.apply_async(kwargs={
            'application_id': application_id,
            'hutk': application.hubspot_context['hutk']
        }, countdown=10)
    elif application.internal_referral_detail != REGISTERED_CLIENT:
        logger.warning("No hutk in Hubspot context", extra=dict(
            type="no_hubspot_context_in_sync_with_hubspot",
            application_id=application_id,
            hubspot_context=application.hubspot_context
        ))
    else:
        logger.info("No hutk in Hubspot context for registered clients. This is normal operation.", extra=dict(
            type="no_hutk_in_hubspot_context_registered_client",
            application_id=application_id
        ))

@message_handler('questionnaire-response')
def get_responses_from_queue(body):
    try:
        convert_response_to_application(body[0][0])
    except Exception as e:
        logger.exception("Failed coverting response to application", exc_info=e, extra=dict(
            type="questionnaire_response_to_application_conversion_failed",
            body=body
        ))
        raise e


@celery_app.task(queue='application-service-tasks')
def update_app_status(application_id):  # pragma: no cover
    application = Application.objects.get(pk=application_id)
    email = application.customer.email

    data = {
        'properties': [
            {
                'property': 'app_status',
                'value': application.stage
            }
        ]
    }
    return hubspot.update_contact(email, data)


@celery_app.task(queue='application-service-tasks')
def send_agent_referral_notification(application_id):
    referral_sign_up_notification = Notification.objects.get(name=Notification.REFERRAL_SIGN_UP)

    if not referral_sign_up_notification.is_active:
        logger.info("referral_sign_up_notification is not active", extra=dict(
            type="referral_sign_up_notification_not_active",
            application_id=application_id,
            referral_sign_up_notification_id=referral_sign_up_notification.id
        ))
        return

    application = Application.objects.get(pk=application_id)
    agent = application.listing_agent
    name = application.customer.name
    first_name = application.customer.get_first_name()
    response = mailer.send_hca_referral_sign_up_notification(agent, name, first_name)
    if response.status_code == 200:
        NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                          notification=referral_sign_up_notification)


@celery_app.task(queue='application-service-tasks')
def send_agent_registration_notification(application_id: uuid.UUID):
    agent_registration_notification = Notification.objects.get(name=Notification.AGENT_REFERRAL_COMPLETE_EMAIL)

    if not agent_registration_notification.is_active:
        logger.info("agent_registration_notification is not active", extra=dict(
            type="agent_registration_notification_not_active",
            application_id=application_id,
            agent_registration_notification_id=agent_registration_notification.id
        ))
        return

    application = Application.objects.get(id=application_id)
    agent = application.listing_agent
    if application.notificationstatus_set.filter(notification=agent_registration_notification).count() == 0:
        response = mailer.send_agent_registration_notification(agent_email=agent.email, agent_first_name=agent.get_first_name(),
                                                               customer_first_name=application.customer.get_first_name())
        if response.status_code == 200:
            NotificationStatus.objects.create(status=NotificationStatus.SENT, application=application,
                                              notification=agent_registration_notification)


@celery_app.task(queue='application-service-tasks')
def push_homeward_user_to_salesforce(user_id: uuid.UUID):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist as err:
        raise Exception("tried pushing user {}, but couldnt find it!".format(user_id)) from err
    try:
        app = Application.objects.get(customer__email=user.email)
    except Application.DoesNotExist:  # Avoid trying to push users who don't actually have an application (ex. CRM logins with no apps)
        return
    if app.new_salesforce: # if the person does not exist in sf yet, we have no record to push the user login data to
        user_sf_payload = user.to_salesforce_representation()
        homeward_salesforce.update_salesforce_object(app.new_salesforce, user_sf_payload, user.salesforce_object_type())


@celery_app.task(queue='application-service-tasks')
def push_to_salesforce(application_id: uuid.UUID):  # pragma: no cover
    try:
        application = Application.objects.get(pk=application_id)
    except Application.DoesNotExist as err:
        raise Exception("tried pushing app {}, but couldnt find it!".format(application_id)) from err
    if application.pushed_to_salesforce_on and application.pushed_to_salesforce_on > application.updated_at:
        return
    if not application.customer.email:
        raise Exception("tried pushing to salesforce, but application {} has no email!".format(application_id))

    try:

        person_id = homeward_salesforce.get_id_by_email(email=application.customer.email)

        homeward_person_data = application.to_salesforce_representation()

        if person_id:
            homeward_salesforce.update_salesforce_object(person_id, homeward_person_data, application.salesforce_object_type())
        else:
            person_id = homeward_salesforce.create_new_salesforce_object(data=homeward_person_data, object_type=application.salesforce_object_type())
    except SalesforceException as e:
        logger.exception("Salesforce raised exception during get/update/create during push", exc_info=e, extra=dict(
            type="salesforce_exception_get_update_create_during_push",
            application_id=application_id
        ))
        return

    Application.objects.filter(pk=application.pk).update(
        new_salesforce=person_id,
        pushed_to_salesforce_on=timezone.now(),
        updated_at=timezone.now())
    push_current_home_to_salesforce(application.id)


@celery_app.task(queue='application-service-tasks')
def push_current_home_to_salesforce(application_id: uuid.UUID):
    """Attepts to push current home data up to Salesforce. Note: The application is needed for the 'new_salesforce' sf id.
    This app salesforce id is put into the current_home payload for Salesforce to link the current home back to the customer/app record."""
    try:
        application = Application.objects.get(pk=application_id)
    except Application.DoesNotExist:
        raise Exception(f"Application ({application_id}) not found when pushing current home to salesforce")

    if application.current_home and application.new_salesforce:
        app_salesforce_id = application.new_salesforce
        try:
            if application.current_home.salesforce_id:
                current_home_salesforce_id = application.current_home.salesforce_id
            else:
                current_home_salesforce_id = homeward_salesforce.get_current_home_id_by_account_id(account_id=app_salesforce_id)

            current_home_data = application.current_home.to_salesforce_representation(app_salesforce_id)

            if current_home_salesforce_id:
                homeward_salesforce.update_salesforce_object(current_home_salesforce_id,
                                                             current_home_data,
                                                             application.current_home.salesforce_object_type())
            else:
                current_home_salesforce_id = homeward_salesforce.create_new_salesforce_object(data=current_home_data,
                                                                                              object_type=application.current_home.salesforce_object_type())
        except SalesforceException as e:
            logger.exception(
                "Salesforce raised exception during get/update/create during push current home",
                exc_info=e, extra=dict(
                    type="salesforce_exception_get_update_create_during_push_current_home",
                    application_id=application_id
                ))
            return

        application.current_home.salesforce_id = current_home_salesforce_id
        application.current_home.save()



@celery_app.task(queue='application-service-tasks')
def push_lead_to_salesforce(lead_id: uuid.UUID):
    try:
        lead = RealEstateLead.objects.get(pk=lead_id)
    except RealEstateLead.DoesNotExist as err:
        raise Exception("tried pushing lead {}, but couldn't find it!".format(lead_id)) from err

    lead_data = lead.to_salesforce_representation()

    try:
        homeward_salesforce.create_new_salesforce_object(data=lead_data, object_type=lead.salesforce_object_type())
    except SalesforceException as e:
        logger.exception(
            "Salesforce raised exception during create during push lead",
            exc_info=e, extra=dict(
                type="salesforce_exception_create_during_push_lead",
                lead_id=lead_id,
                lead_data=lead_data
            ))


@celery_app.task(queue='application-service-tasks')
def push_agent_to_salesforce(application: Application, agent: RealEstateAgent, agent_type: AgentType):

    agent_data = agent.to_salesforce_representation(agent_type)
    try:
        person_id = homeward_salesforce.get_id_by_email(email=application.customer.email)

        if person_id:
            homeward_salesforce.update_salesforce_object(person_id, agent_data, agent.salesforce_object_type())
            Application.objects.filter(pk=application.pk).update(
                pushed_to_salesforce_on=timezone.now(),
                updated_at=timezone.now())
        else:
            logger.warning("Couldn't find customer while syncing agent to salesforce", extra=dict(
                type="cant_find_customer_while_syncing_agent_to_sf",
                application_id=application.id,
                agent_data=agent_data,
                agent_id=agent.id,
                agent_type=agent_type
            ))
    except SalesforceException as e:
        logger.exception(
            "Salesforce raised exception during get/update during push agent",
            exc_info=e, extra=dict(
                type="salesforce_exception_get_update_during_push_agent",
                application_id=application.id,
                agent_data=agent_data,
            ))



@celery_app.task(queue='application-service-tasks')
def push_to_hubspot(application_id=None, force=False):  # pragma: no cover
    try:
        application = Application.objects.get(pk=application_id)
        if application.pushed_to_hubspot_on and force is False:
            return True
    except Application.DoesNotExist:
        return False

    data = {
        'email': application.customer.email,
        'firstname': application.customer.get_first_name(),
        'lastname': application.customer.get_last_name(),
        'phone': application.customer.phone,
        'application_link': application.get_link(),
        'hs_lead_status': str(application.lead_status).upper(),
        'hs_context': json.dumps(getattr(application, 'hubspot_context', {})),
        'app_status': application.stage
    }

    is_successful = hubspot.create(data)

    if is_successful:
        now = timezone.now()
        Application.objects.filter(pk=application.pk).update(updated_at=now, pushed_to_hubspot_on=now)

    return is_successful


@celery_app.task(queue='application-service-tasks')
def get_lead_source_from_hubspot(application_id: uuid.UUID, hutk: str) -> None:
    try:
        lead_source_info = hubspot.get_lead_source_from_hubspot(hutk)
    except hubspot.HubspotContactNotFound:
        push_to_hubspot(application_id, force=True)
        try:
            lead_source_info = hubspot.get_lead_source_from_hubspot(hutk)
        except hubspot.HubspotContactNotFound:
            logger.warning(f"Hubspot data for application {application_id} has not synced, will retry", extra=dict(
                type="hubspot_data_for_application_not_synced_yet",
                application_id=application_id,
                hutk=hutk
            ))
            return

    Application.objects.filter(pk=application_id).update(**lead_source_info)


@periodic_task(run_every=timedelta(hours=24), options={'queue': 'application-service-tasks'})
def delete_s3_pending_uploaded_image():
    """
    Delete pending and uploaded status type of images from s3
    """
    for current_home_image in CurrentHomeImage.objects.filter(
            status__in=['pending', 'uploaded'], updated_at__lte=timezone.now() - timedelta(minutes=30)):
        if aws.delete_object(current_home_image.url):
            current_home_image.delete()


@periodic_task(run_every=timedelta(hours=24), options={'queue': 'application-service-tasks'})
def fill_in_null_lead_source():
    for application in Application.objects.filter(lead_source__isnull=True, hubspot_context__hutk__isnull=False):
        get_lead_source_from_hubspot(application.id, application.hubspot_context['hutk'])


@celery_app.task(queue='application-service-tasks', time_limit=600)
def queue_offer_contract(offer_id: uuid.UUID):
    try:
        pdf = ProcessPdf(offer_id)
        url = pdf.add_data_to_pdf()
        pdf.delete_temp_files()
    except Exception as e:
        logger.exception("Exception raised during queueing offer contract", exc_info=e, extra=dict(
            type="exception_during_queue_offer_contract",
            offer_id=offer_id
        ))
        return

    return url
