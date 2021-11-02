import logging

from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Q

from application.models.acknowledgement import Acknowledgement
from application.models.disclosure import (Disclosure, DisclosureType)

logger = logging.getLogger(__name__)

acknowledgement_defaults = {
    'ip_address': None,
    'is_acknowledged': False
}


def create_service_agreement(application, buying_state, buying_agent_brokerage=None):
    try:
        service_agreement = Disclosure.objects.get(disclosure_type=DisclosureType.SERVICE_AGREEMENT,
                                                   buying_state=buying_state,
                                                   buying_agent_brokerage=buying_agent_brokerage,
                                                   product_offering=application.product_offering,
                                                   active=True)
    except Disclosure.DoesNotExist:
        try:
            service_agreement = Disclosure.objects.get(disclosure_type=DisclosureType.SERVICE_AGREEMENT,
                                                       buying_state=buying_state,
                                                       buying_agent_brokerage=None,
                                                       product_offering=application.product_offering,
                                                       active=True)
        except MultipleObjectsReturned as e:
            logger.exception("Got more than one service agreement", exc_info=e, extra=dict(
                type="multiple_service_agreements_returned",
                application_id=application.id,
                buying_state=buying_state,
                buying_agent_brokerage=buying_agent_brokerage,
                product_offering=application.product_offering,
                disclosure_type=DisclosureType.SERVICE_AGREEMENT
            ))
            return
        except Disclosure.DoesNotExist as e:
            #  this happens when their buying location is out of our service boundaries
            logger.warning("Application buying location is out of our service boundaries", extra=dict(
                type="app_buying_location_out_of_service_boundaries_create_service_agreement",
                application_id=application.id,
                exception_info=e,
            ))
            return
    except MultipleObjectsReturned as e:
        logger.error(f"Got more than one service agreement for application {application.id}", extra=dict(
            type="more_than_one_service_agreement_for_application",
            application_id=application.id,
            exception_info=e,
            buying_state=buying_state,
            buying_agent_brokerage=buying_agent_brokerage,
        ))
        return

    Acknowledgement.objects.get_or_create(application=application, disclosure=service_agreement,
                                          defaults=acknowledgement_defaults)


def create_title_disclosure(application, buying_state, selling_state):
    for disclosure in Disclosure.objects.filter(Q(disclosure_type=DisclosureType.TITLE) &
                                                (Q(buying_state=buying_state) |
                                                 Q(selling_state=selling_state)) & Q(active=True)):
        Acknowledgement.objects.get_or_create(application=application, disclosure=disclosure,
                                              defaults=acknowledgement_defaults)


def create_mortgage_disclosure(application, buying_state):
    try:
        mortgage_disclosure = Disclosure.objects.get(disclosure_type=DisclosureType.MORTGAGE,
                                                     buying_state=buying_state, active=True)
    except MultipleObjectsReturned as e:
        logger.error("Got more than one mortgage disclosure during create for Acknowledgement", extra=dict(
            type="multiple_active_mortgage_disclosures_for_state",
            application_id=application.id,
            buying_state=buying_state,
            disclosure_type=DisclosureType.MORTGAGE,
            exception_info=e
        ))
        return
    except Disclosure.DoesNotExist as e:
        #  this happens when their buying location is out of our service boundaries
        logger.warning("Application buying location is out of our service boundaries", extra=dict(
            type="app_buying_location_out_of_service_boundaries_create_mortgage_disclosure",
            application_id=application.id,
            exception_info=e,
        ))
        return

    Acknowledgement.objects.get_or_create(application=application, disclosure=mortgage_disclosure,
                                          defaults=acknowledgement_defaults)


def create_e_consent_disclosure(application):
    try:
        e_consent_disclosure = Disclosure.objects.get(disclosure_type=DisclosureType.E_CONSENT, active=True)
    except MultipleObjectsReturned as e:
        logger.error("Got more than one e-consent disclosure during create for Acknowledgement", extra=dict(
            type="multiple_active_e_consent_disclosures",
            application_id=application.id,
            disclosure_type=DisclosureType.MORTGAGE,
            exception_info=e
        ))
        return
    except Disclosure.DoesNotExist:
        logger.warning("Disclosure does not exist for type and active status", extra=dict(
            type="no_disclosure_object_for_type_and_active_status",
            disclosure_type=DisclosureType.MORTGAGE,
            active=True,
            application_id=application.id
        ))
        return
    Acknowledgement.objects.get_or_create(application=application, disclosure=e_consent_disclosure,
                                          defaults=acknowledgement_defaults)


def add_acknowledgements(application):
    buying_state = application.get_purchasing_state()
    if buying_state:
        buying_state = buying_state.lower()
    else:
        buying_state = 'no state'

    selling_state = application.get_current_home_state()
    if selling_state:
        selling_state = selling_state.lower()
    else:
        selling_state = 'no state'

    buying_agent_brokerage = application.get_buying_agent_brokerage_name()

    create_e_consent_disclosure(application)
    create_service_agreement(application, buying_state, buying_agent_brokerage)
    create_title_disclosure(application, buying_state, selling_state)
    create_mortgage_disclosure(application, buying_state)
