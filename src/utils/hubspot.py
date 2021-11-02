import json
import logging
import urllib
import urllib.parse
from typing import Dict, List

import requests
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from application import constants
from application.models.customer import Customer
from application.models.internal_support_user import InternalSupportUser
from application.models.new_home_purchase import NewHomePurchase
from application.models.notification import Notification
from application.models.offer import Offer
from application.models.real_estate_agent import RealEstateAgent

logger = logging.getLogger(__name__)


class HubspotException(Exception):
    pass


class HubspotTokenNotFound(HubspotException):
    pass


class HubspotContactNotFound(HubspotException):
    pass


class EmailTemplateNotDefined(Exception):
    pass


URL_ENCODED_HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}
JSON_HEADERS = {'Content-Type': 'application/json'}
FROM_JEFF_YOUNG = "Jeff Young <jeff.young@homeward.com>"
FROM_AGENT_SUCCESS = "Agent Success Team <agent-success@homeward.com>"
FROM_HOMEWARD_NO_REPLY = "Homeward <no-reply@homeward.com>"
FROM_REFERRED_BY_PARTNER = "success-team@homeward.com"
VALUATIONS_TEAM_EMAIL = 'valuationsteam@homeward.com'

token = settings.HUBSPOT.get('API_KEY')
hub = settings.HUBSPOT.get('HUB_ID')
form_guid = settings.HUBSPOT.get('FORM_GUID')

if hub is None:
    raise HubspotException("hubspot hub was not configured properly")
if form_guid is None:
    raise HubspotException("hubspot form guid was not configured properly")
if token is None:
    raise HubspotException("hubspot token was not configured properly")

form_url = 'https://forms.hubspot.com/uploads/form/v2/{}/{}'.format(hub, form_guid)
base_url = "https://api.hubapi.com/"
base_contact_url = "{}contacts/v1/contact".format(base_url)
email_send_url = "{}email/public/v1/singleEmail/send?hapikey={}".format(base_url, token)


def create(data):
    try:
        encoded_data = urllib.parse.urlencode(data)
    except ValueError as e:
        logger.exception("Error encoding data for hubspot", exc_info=e, extra=dict(
            type="hubspot_create_data_encoding_error",
            data=data
        ))
        return False

    result = requests.post(url=form_url, data=encoded_data, headers=URL_ENCODED_HEADERS)

    if result.status_code != 204:
        logger.error("Failed pushing data to hubspot", extra=dict(
            type="failed_pushing_data_to_hubspot_in_create",
            result=result.json() if result else None,
            status_code=result.status_code,
            reason=result.reason
        ))
        return False
    else:
        return True


def update_contact(email, data):
    url = "{}/email/{}/profile?hapikey={}".format(base_contact_url, email, token)
    response = requests.post(url=url, json=data)
    if response.status_code == 204:
        return True
    elif response.status_code == 400:
        logger.error("Problem with request body to Hubspot", extra=dict(
            type="hubspot_bad_request_during_update_contact",
            response=response.json(),
            status_code=response.status_code,
            reason=response.reason
        ))
        return False
    elif response.status_code == 401:
        logger.error("Got unauthorized response from Hubspot", extra=dict(
            type="hubspot_unauthorized_during_update_contact",
            response=response.json(),
            status_code=response.status_code,
            reason=response.reason
        ))
        return False
    elif response.status_code == 404:
        logger.error("Unable to find contact in Hubspot by email", extra=dict(
            type="hubspot_cant_find_contact_by_email_during_update_contact",
            response=response.json(),
            status_code=response.status_code,
            reason=response.reason,
            email=email
        ))
        return False
    elif response.status_code == 500:
        logger.error("Server error on the Hubspot side", extra=dict(
            type="hubspot_server_error_during_update_contact",
            response=response.json(),
            status_code=response.status_code,
            reason=response.reason,
            email=email
        ))
        return False
    else:
        logger.error("Unexpected error during hubspot update contact", extra=dict(
            type="unexpected_error_during_hubspot_update_contact",
            data=data,
            email=email,
            response_reason=response.reason,
            response=response.json()
        ))
        return False


def get_lead_source_from_hubspot(utk: str) -> Dict[str, str]:
    hubspot_data = get_profile_by_hutk(utk)

    properties = hubspot_data.get('properties')

    if properties is None:
        HubspotException("hubspot data didn't have any properties for utk {}".format(utk))

    lead_source = properties.get('hs_analytics_source', {})
    lead_source_drill_down_1 = properties.get('hs_analytics_source_data_1', {})
    lead_source_drill_down_2 = properties.get('hs_analytics_source_data_2', {})

    lead_source_info = {
        "lead_source": lead_source.get('value'),
        "lead_source_drill_down_1": lead_source_drill_down_1.get('value'),
        "lead_source_drill_down_2": lead_source_drill_down_2.get('value')
    }

    return lead_source_info


def get_profile_by_hutk(utk: str) -> Dict[str, str]:
    url = "{}/utk/{}/profile?hapikey={}".format(base_contact_url, utk, token)
    response = requests.get(url=url, headers=URL_ENCODED_HEADERS)
    hubspot_data = json.loads(response.content)
    if response.status_code == 404:
        raise HubspotTokenNotFound("user token {} not found".format(utk))
    elif hubspot_data['is-contact'] is False:
        raise HubspotContactNotFound("user token {} is not a contact".format(utk))

    return hubspot_data


def send_photo_task_complete_notification(first_name, last_name, link):
    if not settings.PHOTO_UPLOAD_NOTIFICATION_EMAIL:
        raise EmailTemplateNotDefined("Unable to send email -- notification email address not configured")

    photo_upload_notification = Notification.objects.get(name=Notification.PHOTO_UPLOAD)
    email_id = photo_upload_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified photo upload notification - skipping")


    data = {
        "emailId": email_id,
        "message": {
            "to": settings.PHOTO_UPLOAD_NOTIFICATION_EMAIL,
            "from": FROM_HOMEWARD_NO_REPLY
        },
        "contactProperties": [
            {"name": "firstname", "value": first_name},
            {"name": "lastname", "value": last_name}
        ],
        "customProperties": [
            {"name": "applicationlink", "value": link}
        ]
    }
    return send_mail(data)


def send_hca_referral_sign_up_notification(agent, customer_name, customer_first_name):
    referral_sign_up_notification = Notification.objects.get(name=Notification.REFERRAL_SIGN_UP)
    email_id = referral_sign_up_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for hca referral sign up notification - skipping")

    data = {
        "emailId": email_id,
        "message": {
            "to": agent.email
        },
        "customProperties": [
            {
                "name": "agent_first_name",
                "value": agent.get_first_name()
            },
            {
                "name": "client_full_name",
                "value": customer_name
            },
            {
                "name": "client_first_name",
                "value": customer_first_name
            }
        ]
    }

    return send_mail(data)


def send_agent_registration_notification(agent_email: str, agent_first_name: str, customer_first_name: str):
    notification = Notification.objects.get(name=Notification.AGENT_REFERRAL_COMPLETE_EMAIL)
    email_id = notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for agent registration notification - skipping")

    data = {
        "emailId": email_id,
        "message": {
            "to": agent_email
        },
        "customProperties": [
            {
                "name": "client_first_name",
                "value": customer_first_name
            },
            {
                "name": "agent_first_name",
                "value": agent_first_name
            }
        ]
    }

    return send_mail(data)


def send_application_under_review(customer_name: str, customer_email: str, application_id: str,
                                  cc_email_list: List[str], loan_advisor_first_name: str = None,
                                  loan_advisor_last_name: str = None, loan_advisor_call_link: str = None,
                                  loan_advisor_phone: str = None):

    application_under_review_notification = Notification.objects.get(name=Notification.APPLICATION_UNDER_REVIEW)
    email_id = application_under_review_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for application under review email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": customer_email,
            "cc": cc_email_list,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer_name
            }
        ],
        "customProperties": [
            {
                "name": "application_id",
                "value": application_id
            },
            {
                "name": "loan_advisor_first_name",
                "value": loan_advisor_first_name
            },
            {
                "name": "loan_advisor_last_name",
                "value": loan_advisor_last_name
            },
            {
                "name": "loan_advisor_phone",
                "value": loan_advisor_phone
            },
            {
                "name": "schedule_a_call_link",
                "value": loan_advisor_call_link
            }
        ]
    }

    return send_mail(data)


def send_unacknowledged_service_agreement_email(customer: Customer):
    unacknowledged_service_agreement_notification = Notification.objects.get(name=Notification.OFFER_REQUESTED_UNACKNOWLEDGED_SERVICE_AGREEMENT)
    email_id = unacknowledged_service_agreement_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for unacknowledged service agreement email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": customer.email
        },
        "customProperties": [
            {
                "name": "first_name",
                "value": customer.get_first_name()
            }
        ]
    }

    return send_mail(data)


def send_offer_submitted(customer: Customer, offer: Offer, offer_price: int, cc_email_list: List[str], from_email: str):
    offer_submitted_notification = Notification.objects.get(name=Notification.OFFER_SUBMITTED)
    email_id = offer_submitted_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for offer submitted email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": customer.email,
            "cc": cc_email_list,
            "from": from_email,
            "replyTo": from_email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer.get_first_name()
            }
        ],
        "customProperties": [
            {
                "name": "new_home_street",
                "value": offer.offer_property_address.street
            },
            {
                "name": "new_home_offer_price",
                "value": f"{round(offer_price):,}"
            }
        ]
    }

    return send_mail(data)


def send_offer_submitted_agent(agent_email: str, agent_name: str, new_home_street: str, cx_first_name: str,
                               cx_last_name: str, homeward_owner_email: str, cc_email_list: List[str]):
    offer_submitted_agent_notification = Notification.objects.get(name=Notification.OFFER_SUBMITTED_AGENT)
    email_id = offer_submitted_agent_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for offer submitted agent email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": agent_email,
            "cc": cc_email_list,
            "from": homeward_owner_email,
            "replyTo": homeward_owner_email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "customProperties": [
            {
                "name": "agent_name",
                "value": agent_name
            },
            {
                "name": "new_home_street",
                "value": new_home_street
            },
            {
                "name": "cx_first_name",
                "value": cx_first_name
            },
            {
                "name": "cx_last_name",
                "value": cx_last_name
            },
        ]
    }

    return send_mail(data)


def send_offer_accepted(customer_email: str, customer_name: str, new_home_purchase: NewHomePurchase,
                        floor_price: str, cc_email_list: List[str], from_email: str):
    offer_accepted_notification = Notification.objects.get(name=Notification.OFFER_ACCEPTED)
    email_id = offer_accepted_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for offer accepted email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": customer_email,
            "cc": cc_email_list,
            "from": from_email,
            "replyTo": from_email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer_name
            }
        ],
        "customProperties": [
            {
                "name": "new_home_street",
                "value": new_home_purchase.address.street
            },
            {
                "name": "post_option_stage_date",
                "value": new_home_purchase.option_period_end_date.strftime("%-m/%-d/%Y")
            },
            {
                "name": "new_home_contract_price",
                "value": f"{round(new_home_purchase.contract_price):,}"
            },
            {
                "name": "rent_amount",
                "value": f"{round(new_home_purchase.rent.amount_months_one_and_two):,}"
            },
            {
                "name": "rent_type",
                "value": new_home_purchase.rent.type
            },
            {
                "name": "earnest_deposit_percentage",
                "value": new_home_purchase.earnest_deposit_percentage
            },
            {
                "name": "floor_price",
                "value": floor_price
            },
        ]
    }

    return send_mail(data)


def send_purchase_price_updated(customer: Customer, preapproval_amount: int, cc_email_list: List[str],
                                contact_first_name: str, contact_last_name: str, contact_email: str,
                                contact_schedule_a_call_url: str):
    purchase_price_updated_notification = Notification.objects.get(name=Notification.PURCHASE_PRICE_UPDATED)
    email_id = purchase_price_updated_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for purchase price updated email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": customer.email,
            "cc": cc_email_list,
            "from": contact_email,
            "replyTo": contact_email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer.get_first_name()
            }
        ],
        "customProperties": [
            {
                "name": "preapproval_amount",
                "value": preapproval_amount
            },
            {
                "name": "contact_first_name",
                "value": contact_first_name
            },
            {
                "name": "contact_last_name",
                "value": contact_last_name
            },
            {
                "name": "schedule_a_call_link",
                "value": contact_schedule_a_call_url
            },
            {
                "name": "contact_email",
                "value": contact_email
            }
        ]
    }

    return send_mail(data)


def send_non_hw_mortgage_candidate_approval(customer_email: str, customer_name: str, preapproval_amount: str,
                                            estimated_down_payment: str, current_home_address: str,
                                            cc_email_list: List[str], from_email: str, cx_first_name: str = None,
                                            cx_last_name: str = None, cx_call_link: str = None, cx_email: str = None,
                                            cx_phone: str = None):

    approval_notification = Notification.objects.get(name=Notification.APPROVAL)
    email_id = approval_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for approval email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": customer_email,
            "cc": cc_email_list,
            "from": from_email,
            "replyTo": from_email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer_name
            }
        ],
        "customProperties": [
            {
                "name": "preapproval_amount",
                "value": preapproval_amount
            },
            {
                "name": "estimated_down_payment",
                "value": estimated_down_payment
            },
            {
                "name": "current_home_address",
                "value": current_home_address
            },
            {
                "name": "cx_first_name",
                "value": cx_first_name
            },
            {
                "name": "cx_last_name",
                "value": cx_last_name
            },
            {
                "name": "schedule_a_call_link",
                "value": cx_call_link
            },
            {
                "name": "cx_email",
                "value": cx_email
            },
            {
                "name": "cx_phone",
                "value": cx_phone
            }
        ]
    }

    return send_mail(data)


def send_hw_mortgage_candidate_approval(customer_email: str, 
                                        homeward_owner_email: str, 
                                        customer_name: str, 
                                        preapproval_amount: str,
                                        estimated_down_payment: str, 
                                        current_home_address: str, 
                                        cc_email_list: List[str], 
                                        loan_advisor_first_name: str = None,
                                        loan_advisor_last_name: str = None, 
                                        loan_advisor_phone: str = None, 
                                        loan_advisor_email: str = None, 
                                        loan_advisor_schedule_a_call_link: str = None, 
                                        ):
    approval_notification = Notification.objects.get(name=Notification.HW_MORTGAGE_CANDIDATE_APPROVAL)
    email_id = approval_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for approval email - skipping")
    
    data = {
        "emailId": int(email_id),
        "message": {
            "to": customer_email,
            "cc": cc_email_list,
            "from": loan_advisor_email,
            "replyTo": loan_advisor_email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer_name,
            }
        ],
        "customProperties": [
            {
                "name": "loan_advisor_first_name",
                "value": loan_advisor_first_name
            },
            {
                "name": "loan_advisor_last_name",
                "value": loan_advisor_last_name
            },
            {
                "name": "loan_advisor_phone",
                "value": loan_advisor_phone
            },
            {
                "name": "loan_advisor_email",
                "value": loan_advisor_email
            },
            {
                "name": "loan_advisor_schedule_a_call_link",
                "value": loan_advisor_schedule_a_call_link
            },
            {
                "name": "preapproval_amount",
                "value": preapproval_amount
            }
        ]
    }
    return send_mail(data)


def send_agent_instructions(agent_name, agent_email: str, customer_name: str, application_id: str,
                            cc_email_list: List[str], from_email: str, cx_first_name: str = None,
                            cx_last_name: str = None, cx_call_link: str = None):
    agent_instructions_notification = Notification.objects.get(name=Notification.AGENT_OFFER_INSTRUCTIONS)
    email_id = agent_instructions_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for agent instructions email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": agent_email,
            "from": from_email,
            "replyTo": from_email,
            "cc": cc_email_list,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "customProperties": [
            {
                "name": "agent_name",
                "value": agent_name
            },
            {
                "name": "customer_name",
                "value": customer_name
            },
            {
                "name": "application_id",
                "value": application_id
            },
            {
                "name": "cx_first_name",
                "value": cx_first_name
            },
            {
                "name": "cx_last_name",
                "value": cx_last_name
            },
            {
                "name": "schedule_a_call_link",
                "value": cx_call_link
            }
        ]
    }

    return send_mail(data)


def send_pre_homeward_close(customer: Customer, new_home_purchase: NewHomePurchase, cc_email_list: List[str],
                            from_email: str):
    pre_homeward_close_notification = Notification.objects.get(name=Notification.PRE_HOMEWARD_CLOSE)
    email_id = pre_homeward_close_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for pre-homeward close email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": customer.email,
            "cc": cc_email_list,
            "from": from_email,
            "replyTo": from_email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer.get_first_name()
            }
        ],
        "customProperties": [
            {
                "name": "estimated_close_date",
                "value": new_home_purchase.homeward_purchase_close_date.strftime("%-m/%-d/%Y")
            },
            {
                "name": "rent_amount",
                "value": f"{round(new_home_purchase.rent.amount_months_one_and_two):,}"
            },
            {
                "name": "rent_type",
                "value": new_home_purchase.rent.type
            },
        ]
    }

    return send_mail(data)


def send_pre_customer_close(customer: Customer, new_home_purchase: NewHomePurchase, cc_email_list: List[str],
                            cx_manager: InternalSupportUser, from_email: str):
    pre_customer_close_notification = Notification.objects.get(name=Notification.PRE_CUSTOMER_CLOSE)
    email_id = pre_customer_close_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for pre-customer close email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": customer.email,
            "cc": cc_email_list,
            "from": cx_manager.email,
            "replyTo": cx_manager.email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer.get_first_name()
            },
        ],
        "customProperties": [
            {
                "name": "estimated_close_date",
                "value": new_home_purchase.customer_purchase_close_date.strftime("%-m/%-d/%Y")
            },
            {
                "name": "cx_first_name",
                "value": cx_manager.first_name
            },
            {
                "name": "cx_last_name",
                "value": cx_manager.last_name
            },
            {
                "name": "schedule_a_call_link",
                "value": cx_manager.schedule_a_call_url
            },
        ]
    }

    return send_mail(data)


def send_expiring_approval_email(customer_email: str, customer_name: str, agent_email: str, homeward_owner_email: str):
    expiring_approval_notification = Notification.objects.get(name=Notification.EXPIRING_APPROVAL)
    email_id = expiring_approval_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for expiring approval email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": customer_email,
            "cc": [agent_email]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer_name
            }
        ]
    }

    return send_mail(data)


def send_agent_pre_customer_close(customer_name: str, agent_name: str, agent_email: str,
                                  address_street: str, close_date: str, homeward_owner_email: str,
                                  transaction_coordinator_email):
    pre_customer_close_agent_notification = Notification.objects.get(name=Notification.AGENT_PRE_CUSTOMER_CLOSE)
    email_id = pre_customer_close_agent_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for agent pre-homeward close email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": agent_email,
            "from": homeward_owner_email,
            "replyTo": homeward_owner_email,
            "cc": [transaction_coordinator_email]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": agent_name
            }
        ],
        "customProperties": [
            {
                "name": "customer_name",
                "value": customer_name
            },
            {
                "name": "new_home_street",
                "value": address_street
            },
            {
                "name": "scheduled_close_date",
                "value": close_date
            },
        ]
    }

    return send_mail(data)


def send_agent_customer_close(agent_name, agent_email, customer_name, new_home_street, homeward_owner_email, transaction_coordinator_email):
    agent_customer_close_notification = Notification.objects.get(name=Notification.AGENT_CUSTOMER_CLOSE)
    email_id = agent_customer_close_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for agent customer close email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": agent_email,
            "from": homeward_owner_email,
            "replyTo": homeward_owner_email,
            "cc": [transaction_coordinator_email],
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": agent_name
            }
        ],
        "customProperties": [
            {
                "name": "customer_name",
                "value": customer_name
            },
            {
                "name": "new_home_street",
                "value": new_home_street
            }
        ]
    }

    return send_mail(data)


def send_homeward_close(customer: Customer, cc_email_list: List[str], from_email: str):
    homeward_close_notification = Notification.objects.get(name=Notification.HOMEWARD_CLOSE)
    email_id = homeward_close_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for homeward close email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": customer.email,
            "cc": cc_email_list,
            "from": from_email,
            "replyTo": from_email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer.get_first_name()
            }
        ]
    }

    return send_mail(data)


def send_customer_close(name: str, email: str, street: str, cc_email_list: List[str],
                        from_email: str):
    customer_close_notification = Notification.objects.get(name=Notification.CUSTOMER_CLOSE)
    email_id = customer_close_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for customer close email - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": email,
            "cc": cc_email_list,
            "from": from_email,
            "replyTo": from_email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": name
            }
        ],
        "customProperties": [
            {
                "name": "new_home_street",
                "value": street
            }
        ]
    }

    return send_mail(data)


def send_incomplete_account_notification(customer: Customer, buying_agent: RealEstateAgent, resume_link: str,
                                         notification_name: str):
    notification = Notification.objects.get(name=notification_name)

    if not notification.template_id:
        raise EmailTemplateNotDefined("no template ID specified for {} - skipping".format(notification.name))

    if buying_agent:
        agent_name = buying_agent.name
        agent_email = buying_agent.email or None
    else:
        agent_name = ""
        agent_email = None

    data = {
        "emailId": int(notification.template_id),
        "message": {
            "to": customer.email,
            "cc": agent_email
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer.get_first_name()
            }
        ],
        "customProperties": [
            {
                "name": "agent_name",
                "value": agent_name
            },
            {
                "name": "resume_link",
                "value": resume_link
            },
            {
                "name": "first_name",
                "value": customer.get_first_name()
            }
        ]
    }
    return send_mail(data)


def send_fast_track_resume_email(buy_agent_email: str, buy_agent_name: str, customer_name: str, customer_first_name: str,
                                 customer_email: str, resume_link: str):
    notification = Notification.objects.get(name=Notification.FAST_TRACK_RESUME)

    if not notification.template_id:
        raise EmailTemplateNotDefined("no template ID specified for fast track resume email - skipping")

    data = {
        "emailId": int(notification.template_id),
        "message": {
            "to": customer_email,
            "cc": buy_agent_email
        },
        "contactProperties": [
            {
                "name": customer_name
            }
        ],
        "customProperties": [
            {
                "name": "agent_name",
                "value": buy_agent_name
            },
            {
                "name": "resume_link",
                "value": resume_link
            },
            {
                "name": "first_name",
                "value": customer_first_name
            }
        ]
    }
    return send_mail(data)


def send_vpal_incomplete_email(buying_agent_email, customer_first_name, customer_email, co_borrower_email, 
                               approval_specialist_email, approval_specialist_first_name, approval_specialist_last_name):
    notification = Notification.objects.get(name=Notification.VPAL_INCOMPLETE)

    if not notification.template_id:
        raise EmailTemplateNotDefined("no template ID specified for VPAL Incomplete - skipping")

    data = {
        "emailId": int(notification.template_id),
        "message": {
            "to": customer_email,
            "from": approval_specialist_email,
            "reply_to": approval_specialist_email,
            "cc": [buying_agent_email, co_borrower_email]
        },
        "customProperties": [
            {
                "name": "first_name",
                "value": customer_first_name
            },
            {
                "name": "approval_specialist_first_name",
                "value": approval_specialist_first_name
            },
            {
                "name": "approval_specialist_last_name",
                "value": approval_specialist_last_name
            }
        ]
    }
    return send_mail(data)


def send_vpal_suspended_email(customer_email, customer_first_name, cc_email_list: List[str], loan_advisor_first_name: str = None,
                              loan_advisor_last_name: str = None, loan_advisor_call_link: str = None, loan_advisor_phone: str = None,
                              loan_advisor_email: str = None, approval_specialist_email: str = None, approval_specialist_first_name: str = None,
                              approval_specialist_last_name: str = None):
    notification = Notification.objects.get(name=Notification.VPAL_SUSPENDED)

    if not notification.template_id:
        raise EmailTemplateNotDefined("no template ID specified for VPAL Suspended - skipping")

    data = {
        "emailId": int(notification.template_id),
        "message": {
            "to": customer_email,
            "from": approval_specialist_email,
            "reply_to": approval_specialist_email,
            "cc": cc_email_list,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "customProperties": [
            {
                "name": "first_name",
                "value": customer_first_name
            },
            {
                "name": "loan_advisor_first_name",
                "value": loan_advisor_first_name
            },
            {
                "name": "loan_advisor_last_name",
                "value": loan_advisor_last_name
            },
            {
                "name": "loan_advisor_phone",
                "value": loan_advisor_phone
            },
            {
                "name": "schedule_a_call_link",
                "value": loan_advisor_call_link
            },
            {
                "name": "loan_advisor_email",
                "value": loan_advisor_email
            },
            {
                "name": "approval_specialist_first_name",
                "value": approval_specialist_first_name
            },
            {
                "name": "approval_specialist_last_name",
                "value": approval_specialist_last_name
            }
        ]
    }
    return send_mail(data)


def send_vpal_ready_for_review_email(customer_first_name, customer_email, co_borrower_email, buying_agent_email, 
                                    approval_specialist_email, approval_specialist_first_name, approval_specialist_last_name):
    notification = Notification.objects.get(name=Notification.VPAL_READY_FOR_REVIEW)

    if not notification.template_id:
        raise EmailTemplateNotDefined("no template ID specified for VPAL Ready For Review - skipping")

    data = {
        "emailId": int(notification.template_id),
        "message": {
            "to": customer_email,
            "from": approval_specialist_email,
            "replyTo": approval_specialist_email,
            "cc": [buying_agent_email, co_borrower_email],
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "customProperties": [
            {
                "name": "first_name",
                "value": customer_first_name
            },
            {
                "name": "approval_specialist_first_name",
                "value": approval_specialist_first_name
            },
            {
                "name": "approval_specialist_last_name",
                "value": approval_specialist_last_name
            }
        ]
    }
    return send_mail(data)


def send_vpal_ready_for_review_follow_up(customer_first_name, customer_last_name, customer_email, co_borrower_email, buying_agent_email):
    notification = Notification.objects.get(name=Notification.VPAL_READY_FOR_REVIEW_FOLLOW_UP)

    if not notification.template_id:
        raise EmailTemplateNotDefined("no template ID specified for VPAL Ready For Review Follow Up - skipping")

    data = {
        "emailId": int(notification.template_id),
        "message": {
            "to": customer_email,
            "cc": [buying_agent_email, co_borrower_email]
        }
    }
    return send_mail(data)


def send_agent_referral_welcome_email(customer: Customer, buying_agent: RealEstateAgent, pricing_link: str):
    notification = Notification.objects.get(name=Notification.AGENT_REFERRAL_CUSTOMER_WELCOME_EMAIL)

    if not notification.template_id:
        raise EmailTemplateNotDefined("no template ID specified for agent referral welcome email - skipping")

    if buying_agent:
        agent_name = buying_agent.name
        agent_email = buying_agent.email or None
    else:
        agent_name = ""
        agent_email = None

    data = {
        "emailId": int(notification.template_id),
        "message": {
            "to": customer.email,
            "cc": agent_email
        },
        "contactProperties": [
            {
                "name": customer.name
            }
        ],
        "customProperties": [
            {
                "name": "agent_name",
                "value": agent_name
            },
            {
                "name": "pricing_link",
                "value": pricing_link
            },
            {
                "name": "first_name",
                "value": customer.get_first_name()
            }
        ]
    }
    return send_mail(data)


def send_cma_request(agent_email, agent_name, customer_name, current_home_street):
    cma_request_notification = Notification.objects.get(name=Notification.CMA_REQUEST)
    email_id = cma_request_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for CMA request - skipping")

    data = {
        "emailId": int(email_id),
        "message": {
            "to": agent_email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": agent_name
            }
        ],
        "customProperties": [
            {
                "name": "customer_name",
                "value": customer_name
            },
            {
                "name": "customer_address_street",
                "value": current_home_street
            }
        ]
    }

    return send_mail(data)


def send_cx_manager_message(cx_manager_email, message, customer_name, customer_email, customer_sf_url):
    cma_request_notification = Notification.objects.get(name=Notification.CX_MESSAGE)
    email_id = cma_request_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for cx message - skipping")

    data = {
        "emailId": email_id,
        "message": {
            "to": cx_manager_email,
            "from": FROM_HOMEWARD_NO_REPLY,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "customProperties": [
            {
                "name": "message",
                "value": message
            },
            {
                "name": "customerName",
                "value": customer_name
            },
            {
                "name": "customerEmail",
                "value": customer_email
            },
            {
                "name": "salesforceURL",
                "value": customer_sf_url
            }
        ]
    }

    return send_mail(data)


def send_incomplete_agent_referral_reminder(agent_email: str, agent_first_name: str, resume_link: str):
    cma_request_notification = Notification.objects.get(name=Notification.INCOMPLETE_REFERRAL)
    email_id = cma_request_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for incomplete referral - skipping")

    data = {
        "emailId": email_id,
        "message": {
            "to": agent_email
        },
        "customProperties": [
            {
                "name": "agent_first_name",
                "value": agent_first_name
            },
            {
                "name": "resume_link",
                "value": resume_link
            }
        ]
    }

    return send_mail(data)


def send_saved_quote_cta(agent_first_name: str, agent_email: str, resume_link: str):
    cma_saved_quote_cta = Notification.objects.get(name=Notification.SAVED_QUOTE)
    email_id = cma_saved_quote_cta.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for saved quote - skipping")

    data = {
        "emailId": email_id,
        "message": {
            "to": agent_email
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": agent_first_name
            }
        ],
        "customProperties": [
            {
                "name": "agent_first_name",
                "value": agent_first_name
            },
            {
                "name": "resume_link",
                "value": resume_link
            }
        ]
    }

    return send_mail(data)


def send_new_customer_partner_email(customer_name, customer_email, customer_phone, home_buying_stage, home_buying_location,
                                    current_home_address, partner_name, partner_email):
    new_customer_partner_email = Notification.objects.get(name=Notification.NEW_CUSTOMER_PARTNER_EMAIL)
    email_id = new_customer_partner_email.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for {} - skipping".format(new_customer_partner_email.name))

    data = {
        "emailId": email_id,
        "message": {
            "to": partner_email,
            "bcc": [constants.HUBSPOT_BCC_EMAIL]
        },
        "customProperties": [
            {
                "name": "customer_name",
                "value": customer_name
            },
            {
                "name": "customer_email",
                "value": customer_email
            },
            {
                "name": "customer_phone",
                "value": customer_phone
            },
            {
                "name": "home_buying_stage",
                "value": home_buying_stage
            },
            {
                "name": "home_buying_location",
                "value": home_buying_location
            },
            {
                "name": "current_home_address",
                "value": current_home_address
            },
            {
                "name": "partner_name",
                "value": partner_name
            }]
    }
    return send_mail(data)


def send_apex_site_pre_account_email(customer_email, customer_first_name, partner_name, resume_link, agent_email):
    apex_site_pre_account_notification = Notification.objects.get(name=Notification.APEX_SITE_PRE_ACCOUNT)
    email_id = apex_site_pre_account_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined("no template ID specified for {} - skipping".format(apex_site_pre_account_notification.name))

    data = {
        "emailId": email_id,
        "message": {
            "to": customer_email,
            "cc": agent_email
        },
        "customProperties": [
            {
                "name": "customer_first_name",
                "value": customer_first_name
            },
            {
                "name": "resume_link",
                "value": resume_link
            },
            {
                "name": "partner_name",
                "value": partner_name
            },
        ]
    }
    return send_mail(data)

def send_application_complete_email(customer_email, customer_first_name, agent_email, 
                                    approval_specialist_first_name, approval_specialist_last_name, approval_specialist_phone_number, approval_specialist_email, loan_advisor_first_name, loan_advisor_last_name):
    application_complete_notification = Notification.objects.get(name=Notification.APPLICATION_COMPLETE)
    email_id = application_complete_notification.template_id
    if not email_id:
        raise EmailTemplateNotDefined(f"no template ID specified for {application_complete_notification.name} - skipping")
    
    data = {
        "emailId": email_id,
        "message": {
            "to": customer_email,
            "from": approval_specialist_email,
            "replyTo": approval_specialist_email,
            "cc": [agent_email, approval_specialist_email],
        },
        "contactProperties": [
            {
                "name": "firstname",
                "value": customer_first_name
            }
        ],
        "customProperties": [
            {
                "name": "loan_advisor_first_name",
                "value": loan_advisor_first_name
            },
            {
                "name": "loan_advisor_last_name",
                "value": loan_advisor_last_name
            },
            {
                "name": "approval_specialist_first_name",
                "value": approval_specialist_first_name
            },
            {
                "name": "approval_specialist_last_name",
                "value": approval_specialist_last_name
            }
        ]
    }
    


def send_mail(data):
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=3, method_whitelist=['POST'], status_forcelist=[500, 502, 503, 504], raise_on_status=False)
    s.mount('https://', HTTPAdapter(max_retries=retries))
    response = s.post(url=email_send_url, data=json.dumps(data, cls=DjangoJSONEncoder), headers=JSON_HEADERS)
    if response.status_code != 200:
        logger.error("Failed to send email", extra=dict(
            type="failed_to_send_hubspot_email",
            response=response.json(),
            reason=response.reason,
            status_code=response.status_code,
            data=data
        ))
    return response

